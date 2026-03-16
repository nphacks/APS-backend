import asyncio
import logging
import json
import base64
import uuid
import os
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver

logger = logging.getLogger(__name__)


class NovaSonicSession:
    """Nova Sonic bidirectional streaming — modeled on AWS sample BedrockStreamManager"""

    # ── Event templates (raw strings, matching AWS sample exactly) ──

    SESSION_START = '{"event":{"sessionStart":{"inferenceConfiguration":{"maxTokens":1024,"topP":0.9,"temperature":0.7}}}}'

    CONTENT_START_AUDIO = '''{
        "event":{
            "contentStart":{
                "promptName":"%s",
                "contentName":"%s",
                "type":"AUDIO",
                "interactive":true,
                "role":"USER",
                "audioInputConfiguration":{
                    "mediaType":"audio/lpcm",
                    "sampleRateHertz":16000,
                    "sampleSizeBits":16,
                    "channelCount":1,
                    "audioType":"SPEECH",
                    "encoding":"base64"
                }
            }
        }
    }'''

    TEXT_CONTENT_START = '''{
        "event":{
            "contentStart":{
                "promptName":"%s",
                "contentName":"%s",
                "type":"TEXT",
                "interactive":false,
                "role":"%s",
                "textInputConfiguration":{"mediaType":"text/plain"}
            }
        }
    }'''

    TEXT_INPUT = '{"event":{"textInput":{"promptName":"%s","contentName":"%s","content":"%s"}}}'

    AUDIO_INPUT = '{"event":{"audioInput":{"promptName":"%s","contentName":"%s","content":"%s"}}}'

    TOOL_CONTENT_START = '''{
        "event":{
            "contentStart":{
                "promptName":"%s",
                "contentName":"%s",
                "interactive":false,
                "type":"TOOL",
                "role":"TOOL",
                "toolResultInputConfiguration":{
                    "toolUseId":"%s",
                    "type":"TEXT",
                    "textInputConfiguration":{"mediaType":"text/plain"}
                }
            }
        }
    }'''

    CONTENT_END = '{"event":{"contentEnd":{"promptName":"%s","contentName":"%s"}}}'
    PROMPT_END = '{"event":{"promptEnd":{"promptName":"%s"}}}'
    SESSION_END = '{"event":{"sessionEnd":{}}}'

    # ── Init ──

    def __init__(self, model_id: str = None, region: str = None):
        env_region = os.getenv('AWS_REGION', 'us-east-1')
        self.region = region or ('us-east-1' if env_region == 'eu-central-1' else env_region)
        self.model_id = model_id or 'amazon.nova-sonic-v1:0'

        self.client = None
        self.stream = None
        self.is_active = False
        self.init_complete = False
        self.audio_input_started = False

        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())

        self.audio_output_queue = asyncio.Queue()
        self.text_output_queue = asyncio.Queue()
        self.audio_input_queue = asyncio.Queue()

        self.role = None
        self.tool_use_id = None
        self.tool_name = None
        self.response_task = None

    def _initialize_client(self):
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        self.client = BedrockRuntimeClient(config=config)

    async def _send_raw(self, event_json: str):
        """Send raw event JSON to the stream."""
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )
        await self.stream.input_stream.send(event)

    def _build_prompt_start(self, tools: list = None) -> str:
        """Build promptStart event as dict then json.dumps (matches AWS sample pattern)."""
        prompt_start = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    }
                }
            }
        }
        if tools:
            tool_specs = []
            for group in tools:
                for fd in group.get("function_declarations", []):
                    tool_specs.append({
                        "toolSpec": {
                            "name": fd["name"],
                            "description": fd["description"],
                            "inputSchema": {"json": json.dumps(fd["parameters"])}
                        }
                    })
            prompt_start["event"]["promptStart"]["toolUseOutputConfiguration"] = {"mediaType": "application/json"}
            prompt_start["event"]["promptStart"]["toolConfiguration"] = {"tools": tool_specs}
        return json.dumps(prompt_start)

    async def start_session(self, system_prompt: str = None, tools: list = None):
        """Start Nova Sonic session — follows AWS sample init order exactly."""
        if system_prompt is None:
            system_prompt = (
                "You are a creative screenplay writing assistant. "
                "Help writers brainstorm ideas, develop characters, and explore story possibilities. "
                "Keep responses conversational and encouraging."
            )

        if not self.client:
            self._initialize_client()

        # Create bidirectional stream
        self.stream = await asyncio.wait_for(
            self.client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            ),
            timeout=60.0
        )
        self.is_active = True

        # Build all init events (matching AWS sample order)
        prompt_event = self._build_prompt_start(tools)
        sys_content_start = self.TEXT_CONTENT_START % (self.prompt_name, self.content_name, "SYSTEM")
        # Escape system prompt for raw JSON string template
        escaped_prompt = system_prompt.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        sys_text = self.TEXT_INPUT % (self.prompt_name, self.content_name, escaped_prompt)
        sys_content_end = self.CONTENT_END % (self.prompt_name, self.content_name)

        # Send all init events with small delays (AWS sample does this)
        init_events = [self.SESSION_START, prompt_event, sys_content_start, sys_text, sys_content_end]
        for evt in init_events:
            await self._send_raw(evt)
            await asyncio.sleep(0.1)

        # Start response processor and audio input loop
        self.response_task = asyncio.create_task(self._process_responses())
        asyncio.create_task(self._send_audio_loop())

        await asyncio.sleep(0.1)
        self.init_complete = True
        print("Nova Sonic session started")

    async def _send_audio_loop(self):
        """Send queued audio chunks to Nova."""
        try:
            while self.is_active:
                chunk = await self.audio_input_queue.get()
                if chunk is None:
                    break
                blob = base64.b64encode(chunk).decode('utf-8')
                audio_event = self.AUDIO_INPUT % (self.prompt_name, self.audio_content_name, blob)
                await self._send_raw(audio_event)
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Audio send loop error: {e}")

    async def _process_responses(self):
        """Process output events from Nova — matches AWS sample pattern."""
        try:
            while self.is_active:
                try:
                    output = await self.stream.await_output()
                    result = await output[1].receive()

                    if not (result.value and result.value.bytes_):
                        continue

                    data = json.loads(result.value.bytes_.decode('utf-8'))
                    if 'event' not in data:
                        continue

                    event = data['event']

                    if 'contentStart' in event:
                        self.role = event['contentStart'].get('role')

                    elif 'textOutput' in event:
                        text = event['textOutput'].get('content', '')
                        if text:
                            # Check for barge-in
                            if '{ "interrupted" : true }' in text:
                                continue
                            await self.text_output_queue.put({
                                "role": "assistant" if self.role == "ASSISTANT" else "user",
                                "text": text
                            })

                    elif 'audioOutput' in event:
                        audio_bytes = base64.b64decode(event['audioOutput']['content'])
                        await self.audio_output_queue.put(audio_bytes)

                    elif 'toolUse' in event:
                        tu = event['toolUse']
                        self.tool_use_id = tu.get('toolUseId')
                        self.tool_name = tu.get('toolName') or tu.get('name')
                        content = tu.get('content', '{}')
                        try:
                            args = json.loads(content) if isinstance(content, str) else content
                        except Exception:
                            args = {}
                        print(f"Tool call: {self.tool_name}({args})")
                        await self.text_output_queue.put({
                            "type": "tool_call",
                            "tool_call": {
                                "function_calls": [{
                                    "name": self.tool_name,
                                    "id": self.tool_use_id,
                                    "args": args
                                }]
                            }
                        })

                    # completionStart, completionEnd, contentEnd, usageEvent — ignore

                except StopAsyncIteration:
                    break
                except Exception as e:
                    error_str = str(e)
                    if "ValidationException" in error_str:
                        logger.warning(f"ValidationException: {error_str}")
                    else:
                        logger.error(f"Response error: {e}")
                    break

        except Exception as e:
            logger.error(f"Response processing fatal: {e}")
        finally:
            if self.is_active:
                await self.text_output_queue.put({"type": "error", "error": "Stream ended unexpectedly"})

    async def start_audio_input(self):
        """Send audio contentStart event."""
        evt = self.CONTENT_START_AUDIO % (self.prompt_name, self.audio_content_name)
        await self._send_raw(evt)

    async def send_audio_chunk(self, audio_bytes: bytes):
        """Queue audio chunk for sending."""
        if not self.is_active or not self.init_complete:
            return
        if not self.audio_input_started:
            await self.start_audio_input()
            self.audio_input_started = True
            await asyncio.sleep(0.05)
        await self.audio_input_queue.put(audio_bytes)

    async def get_audio_output(self):
        return await self.audio_output_queue.get()

    async def get_text_output(self):
        return await self.text_output_queue.get()

    async def send_tool_response(self, function_responses: list):
        """Send tool results back to Nova."""
        if not (self.stream and self.is_active):
            return
        for resp in function_responses:
            cn = str(uuid.uuid4())
            # contentStart for tool result
            await self._send_raw(self.TOOL_CONTENT_START % (self.prompt_name, cn, resp['id']))
            # toolResult
            tool_result = json.dumps({
                "event": {
                    "toolResult": {
                        "promptName": self.prompt_name,
                        "contentName": cn,
                        "content": json.dumps(resp['response']) if isinstance(resp['response'], dict) else resp['response']
                    }
                }
            })
            await self._send_raw(tool_result)
            # contentEnd
            await self._send_raw(self.CONTENT_END % (self.prompt_name, cn))
            print(f"Tool response sent for {resp['name']}")

    async def stop_session(self):
        """Cleanly stop the session."""
        if not self.is_active:
            return
        await self.audio_input_queue.put(None)
        try:
            if self.audio_input_started:
                await self._send_raw(self.CONTENT_END % (self.prompt_name, self.audio_content_name))
            await self._send_raw(self.PROMPT_END % self.prompt_name)
            await self._send_raw(self.SESSION_END)
        except Exception as e:
            logger.warning(f"Stop sequence error (non-fatal): {e}")
        self.is_active = False
        try:
            await self.stream.input_stream.close()
        except Exception:
            pass
