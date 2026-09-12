import os, base64, json
from pathlib import Path

PROMPT = """You are assisting a professional fenestration service engineer.
Analyse the inspection image conservatively.

Return concise JSON only with:
{
  "observations": ["visible factual observations only"],
  "possible_faults": ["possible causes, not certainties"],
  "recommended_checks": ["measurements or physical checks the engineer should perform"],
  "safety_or_limitations": ["anything the image cannot establish"]
}

Rules:
- Never approve a remake, replacement sash, chargeable part, or warranty decision.
- Never claim a dimension unless a readable scale or measurement is visible.
- Distinguish visible evidence from inference.
- If the image is insufficient, say so.
"""

def analyse_image(path: Path):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_VISION_MODEL", "").strip()
    if not api_key or not model:
        return {
            "mode":"not_configured",
            "observations":["Image stored successfully."],
            "possible_faults":[],
            "recommended_checks":[
                "Confirm product and hardware type",
                "Record relevant clearances and dimensions",
                "Check frame level, square and plumb",
                "Test operation with sash/door open where applicable"
            ],
            "safety_or_limitations":["Set OPENAI_API_KEY and OPENAI_VISION_MODEL to enable real vision analysis."]
        }

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    mime = "image/jpeg"
    if path.suffix.lower()==".png": mime="image/png"
    elif path.suffix.lower()==".webp": mime="image/webp"
    data_url = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()

    response = client.responses.create(
        model=model,
        instructions="Return valid JSON only. Do not wrap it in markdown.",
        input=[{
            "role":"user",
            "content":[
                {"type":"input_text","text":PROMPT},
                {"type":"input_image","image_url":data_url,"detail":"high"}
            ]
        }]
    )
    text = response.output_text.strip()
    try:
        result = json.loads(text)
    except Exception:
        result = {
            "observations":[text],
            "possible_faults":[],
            "recommended_checks":[],
            "safety_or_limitations":["Model output could not be parsed as structured JSON."]
        }
    result["mode"]="live_ai"
    return result
