import os
import asyncio
import json
import base64
import logging
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.gemini_live import GeminiLiveSession
from services.nova_sonic import NovaSonicSession

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active sessions
active_sessions = {}


def _graph_headers() -> dict:
    """Build headers for preprod_graph requests, including DigitalOcean API token if set."""
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("DIGITALOCEAN_API_TOKEN")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


async def _call_graph(action: str, payload: dict, timeout: float = 30.0) -> dict:
    """Call preprod_graph — works for both local FastAPI and deployed ADK.
    Local: POST to /{action} with payload.
    Deployed (ADK): POST to base URL with {"action": action, ...payload}."""
    preprod_graph_url = os.getenv("PREPROD_GRAPH_URL", "http://127.0.0.1:2024")
    is_adk = "agents.do-ai.run" in preprod_graph_url

    if is_adk:
        url = preprod_graph_url
        body = {"action": action, **payload}
    else:
        url = f"{preprod_graph_url}/{action}"
        body = payload

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=body, headers=_graph_headers())
        response.raise_for_status()
        return response.json()


async def handle_get_scene(screenplay_id: str, position: str, llm_provider: str = "gemini") -> dict:
    """Handle get_scene_num function call by calling preprod_graph."""
    try:
        result = await _call_graph("get-scene", {
            "screenplay_id": screenplay_id,
            "position": position,
            "llm_provider": llm_provider
        })
        return {
            "formatted_scene": result.get("formatted_scene", "Scene not found"),
            "scene_index": result.get("scene_index", -1)
        }
    except Exception as e:
        logger.error(f"Error calling preprod_graph: {e}")
        return {"formatted_scene": f"Error calling preprod_graph: {e}", "scene_index": -1}


async def handle_get_scene_by_content(screenplay_id: str, query: str, llm_provider: str = "gemini") -> dict:
    """Handle get_scene_by_content function call by calling preprod_graph."""
    try:
        result = await _call_graph("get-scene-by-content", {
            "screenplay_id": screenplay_id,
            "query": query,
            "llm_provider": llm_provider
        })
        return {
            "formatted_scene": result.get("formatted_scene", "Scene not found"),
            "scene_index": result.get("scene_index", -1)
        }
    except Exception as e:
        logger.error(f"Error calling preprod_graph: {e}")
        return {"formatted_scene": f"Error calling preprod_graph: {e}", "scene_index": -1}


async def handle_brainstorm(screenplay_id: str, tidb_screenplay_id: str, query: str = "", llm_provider: str = "gemini") -> dict:
    """Handle brainstorm_ideas function call by calling preprod_graph."""
    try:
        result = await _call_graph("brainstorm", {
            "screenplay_id": screenplay_id,
            "tidb_screenplay_id": tidb_screenplay_id,
            "query": query,
            "llm_provider": llm_provider
        }, timeout=60.0)
        return {"response": result.get("response", "No ideas generated")}
    except Exception as e:
        logger.error(f"Error calling preprod_graph brainstorm: {e}")
        return {"response": f"Error: {e}"}


async def handle_get_project_info(project_id: str, llm_provider: str = "gemini") -> dict:
    """Handle get_project_info function call by calling preprod_graph."""
    try:
        result = await _call_graph("get-project-info", {
            "project_id": project_id,
            "llm_provider": llm_provider
        })
        return {"response": result.get("response", "No project info found")}
    except Exception as e:
        logger.error(f"Error calling preprod_graph get-project-info: {e}")
        return {"response": f"Error: {e}"}


async def handle_create_scene(screenplay_id: str, narration: str, llm_provider: str = "gemini") -> dict:
    """Handle create_scene function call by calling preprod_graph."""
    try:
        result = await _call_graph("create-scene", {
            "screenplay_id": screenplay_id,
            "narration": narration,
            "llm_provider": llm_provider
        }, timeout=60.0)
        return {
            "scene": result.get("scene", {}),
            "response": result.get("response", "Error creating scene")
        }
    except Exception as e:
        logger.error(f"Error calling preprod_graph create-scene: {e}")
        return {"scene": {}, "response": f"Error: {e}"}


async def handle_update_scene(screenplay_id: str, query: str, llm_provider: str = "gemini") -> dict:
    """Handle update_scene function call by calling preprod_graph."""
    try:
        result = await _call_graph("update-scene", {
            "screenplay_id": screenplay_id,
            "query": query,
            "llm_provider": llm_provider
        }, timeout=60.0)
        return {
            "scene": result.get("scene", {}),
            "scene_index": result.get("scene_index", -1),
            "response": result.get("response", "Error updating scene")
        }
    except Exception as e:
        logger.error(f"Error calling preprod_graph update-scene: {e}")
        return {"scene": {}, "scene_index": -1, "response": f"Error: {e}"}


async def handle_approve_scene(screenplay_id: str, scene: dict) -> dict:
    """Save an approved scene to the screenplay via backend."""
    try:
        backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{backend_url}/api/screenplay/scenes/add",
                json={"mongodb_id": screenplay_id, "scene": scene}
            )
            response.raise_for_status()
            result = response.json()
        return {
            "scene": result.get("scene", scene),
            "scene_index": result.get("scene_index", -1)
        }
    except Exception as e:
        logger.error(f"Error saving scene: {e}")
        return {"scene": scene, "scene_index": -1, "error": str(e)}


async def handle_update_scene_approve(screenplay_id: str, scene: dict, scene_index: int) -> dict:
    """Save an approved scene update to the screenplay via backend."""
    try:
        backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{backend_url}/api/screenplay/scenes/update",
                json={"mongodb_id": screenplay_id, "scene_index": scene_index, "scene": scene}
            )
            response.raise_for_status()
            result = response.json()
        return {
            "scene": result.get("scene", scene),
            "scene_index": result.get("scene_index", scene_index)
        }
    except Exception as e:
        logger.error(f"Error updating scene: {e}")
        return {"scene": scene, "scene_index": scene_index, "error": str(e)}


async def handle_update_project_info(project_id: str, query: str, llm_provider: str = "gemini") -> dict:
    """Handle update_project_info function call by calling preprod_graph."""
    try:
        result = await _call_graph("update-project-info", {
            "project_id": project_id,
            "query": query,
            "llm_provider": llm_provider
        })
        return {"response": result.get("response", "No update performed")}
    except Exception as e:
        logger.error(f"Error calling preprod_graph update-project-info: {e}")
        return {"response": f"Error: {e}"}
    except Exception as e:
        logger.error(f"Error calling preprod_graph update-project-info: {e}")
        return {"response": f"Error: {e}"}


@router.websocket("/voice")
async def voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice interaction."""
    await websocket.accept()
    session_id = id(websocket)
    session = None

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            # ── START SESSION ──
            if msg_type == "start":
                service = message.get("service", "gemini")
                screenplay_id = message.get("screenplay_id")
                tidb_screenplay_id = message.get("tidb_screenplay_id", "")
                project_id = message.get("project_id", "")
                system_prompt = message.get("system_prompt")
                print(f"Voice session starting: service={service}, screenplay={screenplay_id}, tidb={tidb_screenplay_id}, project={project_id}")

                if not screenplay_id:
                    await websocket.send_text(json.dumps({"type": "error", "error": "screenplay_id is required"}))
                    continue

                # Define tools
                tools = [{
                    "function_declarations": [
                        {
                            "name": "get_scene_num",
                            "description": "Get a specific scene from the screenplay by position. Use this when user asks about 'last scene', 'first scene', 'second scene', 'third last scene', etc.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "position": {
                                        "type": "string",
                                        "description": "Position of the scene: 'last', 'first', 'second', 'third', 'second last', 'third last', etc."
                                    }
                                },
                                "required": ["position"]
                            }
                        },
                        {
                            "name": "get_scene_by_content",
                            "description": "Find a scene by its content or dialogue. Use this when user asks about a scene by describing what happens in it, quoting dialogue, or referencing specific content. Examples: 'the scene where they argue about the plan', 'the scene with the car chase', 'where she says goodbye'.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The user's description of the scene content or dialogue they are looking for."
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "brainstorm_ideas",
                            "description": "Brainstorm and suggest ideas for the next scene. Use this when user asks for help with what to write next, wants suggestions, ideas, or asks about which beats are left to cover. Examples: 'what should happen next', 'give me ideas for the next scene', 'brainstorm', 'what beats are left'.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Optional context from the user about what kind of ideas they want. Can be empty."
                                    }
                                },
                                "required": []
                            }
                        },
                        {
                            "name": "get_project_info",
                            "description": "Get project information like title, description, and list of screenplays. Use this when user asks about the project, its name, description, or what screenplays exist. Examples: 'what is this project about', 'project name', 'what screenplays do we have', 'tell me about the project'.",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "create_scene",
                            "description": "Create a new scene from the user's narration/description. Use this when the user describes a scene they want to add to the screenplay. The user will narrate the scene including setting, action, characters, and dialogue. Wait for the user to finish narrating (key phrases: 'end scene', 'that's it', 'that's the scene') before calling this tool.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "narration": {
                                        "type": "string",
                                        "description": "The full narration/description of the scene from the user, including setting, action, characters, dialogue, and any other details."
                                    }
                                },
                                "required": ["narration"]
                            }
                        },
                        {
                            "name": "update_project_info",
                            "description": "Update the project name or description. Use this when the user wants to change, rename, or update the project title or description. Examples: 'change the project name to...', 'update the description to...', 'rename the project'.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The user's instruction about what to update, e.g. 'change the name to My New Project' or 'set the description to A thriller about...'"
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "update_scene",
                            "description": "Update an existing scene in the screenplay. Use this when the user wants to edit, change, modify, or fix a specific scene. The user should identify which scene (by position like 'last scene' or by content like 'the scene in the kitchen') and describe what changes to make. Wait for the user to finish describing all changes before calling this tool.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The user's full instruction including which scene to update and what changes to make. e.g. 'in the last scene, change the dialogue where John says hello to goodbye' or 'update the kitchen scene to add a parenthetical for whispering'"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    ]
                }]

                # Initialize session
                if service == "nova":
                    session = NovaSonicSession()
                else:
                    api_key = os.getenv("GOOGLE_API_KEY")
                    if not api_key:
                        await websocket.send_text(json.dumps({"type": "error", "error": "GOOGLE_API_KEY not configured"}))
                        continue
                    session = GeminiLiveSession(api_key=api_key)

                active_sessions[session_id] = {
                    "session": session,
                    "screenplay_id": screenplay_id,
                    "tidb_screenplay_id": tidb_screenplay_id,
                    "project_id": project_id,
                    "service": service
                }

                # Start session (non-blocking)
                asyncio.create_task(session.start_session(system_prompt, tools))

                # Wait for init to complete (up to 10 seconds)
                for _ in range(100):
                    if hasattr(session, 'init_complete') and session.init_complete:
                        break
                    if session.is_active and not hasattr(session, 'init_complete'):
                        break  # Gemini doesn't have init_complete
                    await asyncio.sleep(0.1)

                print(f"Session ready: is_active={session.is_active}")

                # Forward audio from service → frontend
                async def forward_audio():
                    while not session.is_active:
                        await asyncio.sleep(0.1)
                    try:
                        while session.is_active:
                            audio_bytes = await session.get_audio_output()
                            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                            try:
                                await websocket.send_text(json.dumps({"type": "audio", "audio": audio_b64}))
                            except RuntimeError:
                                return
                    except Exception as e:
                        logger.error(f"forward_audio error: {e}")

                # Forward text/tool calls from service → frontend
                async def forward_text():
                    while not session.is_active:
                        await asyncio.sleep(0.1)
                    try:
                        while session.is_active:
                            text_data = await session.get_text_output()

                            # Handle tool calls
                            if text_data.get("type") == "tool_call":
                                tool_call = text_data["tool_call"]
                                fc_list = []
                                if hasattr(tool_call, 'function_calls'):
                                    fc_list = tool_call.function_calls
                                elif isinstance(tool_call, dict):
                                    fc_list = tool_call.get("function_calls", [])

                                function_responses = []
                                for fc in fc_list:
                                    fc_name = fc.name if hasattr(fc, 'name') else fc.get('name')
                                    fc_id = fc.id if hasattr(fc, 'id') else fc.get('id')
                                    fc_args = fc.args if hasattr(fc, 'args') else fc.get('args', {})

                                    # Send tool status to frontend
                                    tool_labels = {
                                        "get_scene_num": "Fetching scene...",
                                        "get_scene_by_content": "Searching scenes...",
                                        "brainstorm_ideas": "Brainstorming ideas...",
                                        "get_project_info": "Getting project info...",
                                        "create_scene": "Creating scene...",
                                        "update_project_info": "Updating project...",
                                        "update_scene": "Updating scene..."
                                    }
                                    try:
                                        await websocket.send_text(json.dumps({
                                            "type": "tool_status",
                                            "tool": fc_name,
                                            "label": tool_labels.get(fc_name, "Processing..."),
                                            "status": "running"
                                        }))
                                    except RuntimeError:
                                        pass

                                    if fc_name == "get_scene_num":
                                        sd = active_sessions.get(session_id, {})
                                        scene_result = await handle_get_scene(
                                            screenplay_id=sd.get("screenplay_id", ""),
                                            position=fc_args.get("position"),
                                            llm_provider=sd.get("service", "gemini")
                                        )
                                        function_responses.append({
                                            "name": fc_name,
                                            "id": fc_id,
                                            "response": {"result": scene_result["formatted_scene"]}
                                        })
                                        # Send highlight command to frontend
                                        if scene_result.get("scene_index", -1) >= 0:
                                            try:
                                                await websocket.send_text(json.dumps({
                                                    "type": "highlight_scene",
                                                    "scene_index": scene_result["scene_index"]
                                                }))
                                            except RuntimeError:
                                                pass

                                    elif fc_name == "get_scene_by_content":
                                        sd = active_sessions.get(session_id, {})
                                        scene_result = await handle_get_scene_by_content(
                                            screenplay_id=sd.get("screenplay_id", ""),
                                            query=fc_args.get("query", ""),
                                            llm_provider=sd.get("service", "gemini")
                                        )
                                        function_responses.append({
                                            "name": fc_name,
                                            "id": fc_id,
                                            "response": {"result": scene_result["formatted_scene"]}
                                        })
                                        # Send highlight command to frontend
                                        if scene_result.get("scene_index", -1) >= 0:
                                            try:
                                                await websocket.send_text(json.dumps({
                                                    "type": "highlight_scene",
                                                    "scene_index": scene_result["scene_index"]
                                                }))
                                            except RuntimeError:
                                                pass

                                    elif fc_name == "brainstorm_ideas":
                                        sd = active_sessions.get(session_id, {})
                                        brainstorm_result = await handle_brainstorm(
                                            screenplay_id=sd.get("screenplay_id", ""),
                                            tidb_screenplay_id=sd.get("tidb_screenplay_id", ""),
                                            query=fc_args.get("query", ""),
                                            llm_provider=sd.get("service", "gemini")
                                        )
                                        function_responses.append({
                                            "name": fc_name,
                                            "id": fc_id,
                                            "response": {"result": brainstorm_result["response"]}
                                        })

                                    elif fc_name == "get_project_info":
                                        sd = active_sessions.get(session_id, {})
                                        project_result = await handle_get_project_info(
                                            project_id=sd.get("project_id", ""),
                                            llm_provider=sd.get("service", "gemini")
                                        )
                                        function_responses.append({
                                            "name": fc_name,
                                            "id": fc_id,
                                            "response": {"result": project_result["response"]}
                                        })

                                    elif fc_name == "create_scene":
                                        sd = active_sessions.get(session_id, {})
                                        create_result = await handle_create_scene(
                                            screenplay_id=sd.get("screenplay_id", ""),
                                            narration=fc_args.get("narration", ""),
                                            llm_provider=sd.get("service", "gemini")
                                        )
                                        function_responses.append({
                                            "name": fc_name,
                                            "id": fc_id,
                                            "response": {"result": create_result["response"]}
                                        })
                                        # Send preview to frontend for approval
                                        if create_result.get("scene"):
                                            # Store pending scene in session
                                            sd["pending_scene"] = create_result["scene"]
                                            try:
                                                await websocket.send_text(json.dumps({
                                                    "type": "preview_scene",
                                                    "scene": create_result["scene"]
                                                }))
                                            except RuntimeError:
                                                pass

                                    elif fc_name == "update_project_info":
                                        sd = active_sessions.get(session_id, {})
                                        update_result = await handle_update_project_info(
                                            project_id=sd.get("project_id", ""),
                                            query=fc_args.get("query", ""),
                                            llm_provider=sd.get("service", "gemini")
                                        )
                                        function_responses.append({
                                            "name": fc_name,
                                            "id": fc_id,
                                            "response": {"result": update_result["response"]}
                                        })

                                    elif fc_name == "update_scene":
                                        sd = active_sessions.get(session_id, {})
                                        update_result = await handle_update_scene(
                                            screenplay_id=sd.get("screenplay_id", ""),
                                            query=fc_args.get("query", ""),
                                            llm_provider=sd.get("service", "gemini")
                                        )
                                        function_responses.append({
                                            "name": fc_name,
                                            "id": fc_id,
                                            "response": {"result": update_result["response"]}
                                        })
                                        # Send preview to frontend for approval
                                        if update_result.get("scene"):
                                            sd["pending_scene"] = update_result["scene"]
                                            sd["pending_scene_index"] = update_result.get("scene_index", -1)
                                            try:
                                                await websocket.send_text(json.dumps({
                                                    "type": "preview_scene",
                                                    "scene": update_result["scene"],
                                                    "scene_index": update_result.get("scene_index", -1),
                                                    "is_update": True
                                                }))
                                            except RuntimeError:
                                                pass

                                if function_responses:
                                    print(f"Sending tool response: {function_responses[0]['name']}")
                                    await session.send_tool_response(function_responses)
                                    # Clear tool status
                                    try:
                                        await websocket.send_text(json.dumps({
                                            "type": "tool_status",
                                            "tool": function_responses[0]['name'],
                                            "label": "",
                                            "status": "done"
                                        }))
                                    except RuntimeError:
                                        pass

                            elif text_data.get("type") == "error":
                                try:
                                    await websocket.send_text(json.dumps({"type": "error", "error": text_data.get("error", "Unknown error")}))
                                except RuntimeError:
                                    return
                            else:
                                try:
                                    await websocket.send_text(json.dumps({"type": "text", **text_data}))
                                except RuntimeError:
                                    return
                    except Exception as e:
                        logger.error(f"forward_text error: {e}")

                asyncio.create_task(forward_audio())
                asyncio.create_task(forward_text())

                await websocket.send_text(json.dumps({"type": "session_started", "service": service}))
                print(f"Session started: {service}")

            # ── AUDIO INPUT ──
            elif msg_type == "audio":
                if session_id not in active_sessions:
                    continue
                session = active_sessions[session_id]["session"]
                audio_b64 = message.get("audio", "")
                if audio_b64:
                    await session.send_audio_chunk(base64.b64decode(audio_b64))

            # ── STOP SESSION ──
            elif msg_type == "stop":
                if session_id in active_sessions:
                    session = active_sessions[session_id]["session"]
                    await session.stop_session()
                    del active_sessions[session_id]
                    await websocket.send_text(json.dumps({"type": "session_stopped"}))

            # ── APPROVE SCENE ──
            elif msg_type == "approve_scene":
                if session_id in active_sessions:
                    sd = active_sessions[session_id]
                    pending = sd.get("pending_scene")
                    pending_index = sd.get("pending_scene_index")
                    if pending:
                        if pending_index is not None and pending_index >= 0:
                            # Update existing scene
                            save_result = await handle_update_scene_approve(
                                screenplay_id=sd.get("screenplay_id", ""),
                                scene=pending,
                                scene_index=pending_index
                            )
                        else:
                            # Add new scene
                            save_result = await handle_approve_scene(
                                screenplay_id=sd.get("screenplay_id", ""),
                                scene=pending
                            )
                        sd["pending_scene"] = None
                        sd["pending_scene_index"] = None
                        if save_result.get("error"):
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "error": f"Failed to save scene: {save_result['error']}"
                            }))
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "scene_approved",
                                "scene": save_result["scene"],
                                "scene_index": save_result["scene_index"]
                            }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": "No pending scene to approve"
                        }))

            # ── REJECT SCENE ──
            elif msg_type == "reject_scene":
                if session_id in active_sessions:
                    active_sessions[session_id]["pending_scene"] = None
                    active_sessions[session_id]["pending_scene_index"] = None
                    await websocket.send_text(json.dumps({"type": "scene_rejected"}))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "error": str(e)}))
        except:
            pass
    finally:
        if session_id in active_sessions:
            try:
                await active_sessions[session_id]["session"].stop_session()
            except:
                pass
            del active_sessions[session_id]
