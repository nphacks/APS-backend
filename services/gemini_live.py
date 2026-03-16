import asyncio
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiLiveSession:
    """Handles streaming voice interaction with Gemini Live API"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-native-audio-preview-12-2025"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1alpha"}
        )
        self.audio_input_queue = asyncio.Queue()
        self.audio_output_queue = asyncio.Queue()
        self.text_output_queue = asyncio.Queue()
        self.is_active = False
        self.session = None
        
    async def start_session(self, system_prompt: str = None, tools: list = None):
        """Start a Gemini Live session with streaming audio"""
        
        if system_prompt is None:
            system_prompt = """You are a creative screenplay writing assistant. 
Help writers brainstorm ideas, develop characters, and explore story possibilities.
Keep responses conversational and encouraging."""
        
        # Use dict-based config for compatibility
        config = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": "Puck"
                    }
                }
            },
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            }
        }
        
        if tools:
            config["tools"] = tools
        
        self.is_active = True
        
        async with self.client.aio.live.connect(model=self.model, config=config) as session:
            self.session = session
            
            # Task to send audio input
            async def send_audio():
                try:
                    while self.is_active:
                        chunk = await self.audio_input_queue.get()
                        if chunk is None:  # Stop signal
                            break
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=chunk,
                                mime_type="audio/pcm;rate=16000"
                            )
                        )
                except asyncio.CancelledError:
                    pass
            
            # Task to receive responses
            async def receive_responses():
                try:
                    while self.is_active:
                        async for response in session.receive():
                            server_content = response.server_content
                            tool_call = response.tool_call
                            
                            if server_content:
                                # Handle audio output
                                if server_content.model_turn:
                                    for part in server_content.model_turn.parts:
                                        if part.inline_data:
                                            logger.info(f"Received audio chunk: {len(part.inline_data.data)} bytes")
                                            await self.audio_output_queue.put(
                                                part.inline_data.data
                                            )
                                
                                # Handle transcriptions
                                if server_content.output_transcription:
                                    text = server_content.output_transcription.text
                                    if text:
                                        logger.info(f"Output transcription: {text}")
                                        await self.text_output_queue.put({
                                            "role": "assistant",
                                            "text": text
                                        })
                                
                                if server_content.input_transcription:
                                    text = server_content.input_transcription.text
                                    if text:
                                        logger.info(f"Input transcription: {text}")
                                        await self.text_output_queue.put({
                                            "role": "user",
                                            "text": text
                                        })
                                
                                # Handle interruptions
                                if server_content.interrupted:
                                    logger.info("Conversation interrupted")
                                    await self.text_output_queue.put({
                                        "type": "interrupted"
                                    })
                                
                                # Handle turn complete
                                if server_content.turn_complete:
                                    logger.info("Turn complete")
                                    await self.text_output_queue.put({
                                        "type": "turn_complete"
                                    })
                            
                            # Handle tool calls
                            if tool_call:
                                logger.info(f"Tool call received: {tool_call}")
                                await self.text_output_queue.put({
                                    "type": "tool_call",
                                    "tool_call": tool_call
                                })
                
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error in receive_responses: {e}")
                    await self.text_output_queue.put({
                        "type": "error",
                        "error": str(e)
                    })
            
            # Start both tasks
            send_task = asyncio.create_task(send_audio())
            receive_task = asyncio.create_task(receive_responses())
            
            try:
                # Wait for both tasks
                await asyncio.gather(send_task, receive_task)
            finally:
                self.is_active = False
                send_task.cancel()
                receive_task.cancel()
    
    async def send_audio_chunk(self, audio_bytes: bytes):
        """Send audio chunk to Gemini"""
        if self.is_active:
            await self.audio_input_queue.put(audio_bytes)
    
    async def get_audio_output(self):
        """Get audio output from Gemini"""
        return await self.audio_output_queue.get()
    
    async def get_text_output(self):
        """Get text transcription from Gemini"""
        return await self.text_output_queue.get()
    
    async def send_tool_response(self, function_responses: list):
        """Send tool response back to Gemini"""
        if self.session and self.is_active:
            await self.session.send_tool_response(function_responses=function_responses)
    
    async def stop_session(self):
        """Stop the session"""
        self.is_active = False
        await self.audio_input_queue.put(None)  # Stop signal
