PRD: Zero-Friction Vision Pipeline ("Home vs. Wild")
1. Objective
Eliminate measurement friction for users managing PCOD. Users must be able to log a meal using only a photograph and a binary context toggle, bypassing manual weight estimation entirely while maintaining macro accuracy.

2. Core Flow

User snaps a photo of their meal.

User selects an environment context: Home (standard personal kitchenware) or Wild (restaurant/hospitality sizing).

Payload (base64 image + context string) is sent to the backend.

gemma4:e2b vision model analyzes the image, applies the context heuristic, and extracts food names and estimated weights in grams.

Extraction is passed to the existing parallel nutrition pipeline (Two-Pass LLM + Atwater Guardrail) to finalize macros and save to SQLite.

3. Scope & Constraints

In Scope: prompts.yaml update, ExtractionService vision method, new FastAPI endpoint (POST /vision-log), integration with existing Two-Pass text pipeline.

Out of Scope: Dynamic utensil RAG lookups, multi-turn chat for image clarification.

Hardware Constraint: Must run locally on MSI GL66 (8GB VRAM) using ollama/gemma4:e2b.

The Issue Tracker
We break this PRD into three atomic engineering issues.

Issue #1: Define Vision Prompt Schema

Task: Inject the vision_estimate template into prompts.yaml.

Requirement: Must handle {environment} injection and enforce strict JSON output ({"items": [{"name": "...", "grams": ...}]}).

Issue #2: Multimodal Extraction Service

Task: Implement extract_from_image(self, base64_image: str, environment: str) in app/services/extraction.py.

Requirement: Must properly format the LiteLLM/Ollama multimodal message payload array (Text + Image URL) and parse the returned JSON string into Python dictionaries.

Issue #3: The API Bridge & Pipeline Wiring

Task: Create POST /vision-log in app/api.py.

Requirement: Must accept a Pydantic schema for the request (image_base64, environment). Must pipe the output of extract_from_image directly into the existing _process_base_ingredient and GoalRequest flow.

TDD Strategy (The Red-Green Plan)
Following your TESTING_INSTRUCTIONS.md, we will write the tests before we touch the application code.

Red Phase 1: Test the Prompt Formatting

Test: Assert that prompts.yaml contains the vision_estimate key and that it formats correctly without throwing KeyError.

Red Phase 2: Test the Multimodal Service (Mocked)

Test: Pass a dummy base64 string to extract_from_image. Mock the litellm.acompletion response to return a valid JSON string. Assert that the service correctly parses the string into a list of dictionaries.

Test Edge Case: Mock the LLM returning garbage (Markdown block) and assert your JSON cleaner handles it.

Red Phase 3: Test the API Endpoint

Test: Use httpx.AsyncClient to hit /vision-log with a mock payload. Mock the extract_from_image to bypass the actual LLM, but let it run through the real foodbank.db pipeline. Assert the endpoint returns a 200 OK and a valid FoodLogResponse.