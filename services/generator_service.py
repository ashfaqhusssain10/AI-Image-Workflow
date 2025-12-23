import time
import os
import requests
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

class GeneratorService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        # Use the newer SDK client
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        
        # Use the model specified or default to the one from the reference file
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image") 

    def generate_image(self, prompt_text, ref_image_url, background_path, angle_path):
        """
        Generates an image using Google GenAI (v2 SDK), following the 'Beige' prompt strategy.
        """
        print(f"DEBUG: Generating image with model: {self.model_name}")
        print(f"DEBUG: Ref URL: {ref_image_url}")
        print(f"DEBUG: Bg Path: {background_path}")
        print(f"DEBUG: Angle Path: {angle_path}")

        try:
            # 1. Load Images
            # Reference Image (from S3 URL)
            response = requests.get(ref_image_url)
            response.raise_for_status()
            food_ref_bytes = response.content

            # Background Image (Local)
            with open(background_path, 'rb') as f:
                bg_bytes = f.read()

            # Angle Image (Local)
            with open(angle_path, 'rb') as f:
                angle_bytes = f.read()

            # 2. Construct Prompt (Beige Strategy)
            item_name = str(prompt_text) 

            enhanced_prompt = f"""
    CRITICAL TASK: Generate a photorealistic image of {item_name}

    ⚠️ MANDATORY SYNTHESIS PROCESS:
    ═══════════════════════════════════════════════════════════
    YOU MUST CREATE A NEW IMAGE BY COMBINING:
    1. EXTRACT food appearance from Image 1 (Food Reference)
    2. UNDERSTAND camera angle from Image 3 (Angle Reference)
    3. PLACE extracted food onto Image 2 (Background Canvas)
    4. SYNTHESIZE these elements into a NEW composition

    IMAGE USAGE RULES:
    🔴 Image 1 (Food Reference): Extract FOOD APPEARANCE ONLY
       - Colors, textures, garnishes of the food
       - DO NOT copy its angle, vessel, or background

    🟡 Image 2 (Background Canvas): Use as CANVAS ONLY
       - This is your final background surface

    🟢 Image 3 (Angle Reference): Extract CAMERA ANGLE ONLY
       - Understand the viewing perspective
       - DO NOT use any food, vessel, or elements from this image

    SYNTHESIS REQUIREMENTS:
    1. Take the {item_name} appearance from Image 1
    2. Mentally rotate/transform it to match Image 3's angle
    3. Place transformed food in a fresh vessel appropriate for the dish
    4. Composite onto Image 2's surface
    5. Add proper shadows and lighting matching the background
    """

            # 3. Call GenAI using the new SDK syntax (types.Part)
            # Order: Food (Ref), Bg, Angle, Prompt
            
            content_parts = []
            
            # Image 1: FOOD
            content_parts.append(types.Part(text="🔴 PRIMARY IMAGE - FOOD REFERENCE:"))
            content_parts.append(types.Part(
                inline_data=types.Blob(
                    mime_type='image/jpeg', 
                    data=food_ref_bytes
                )
            ))
            
            # Image 2: BACKGROUND
            content_parts.append(types.Part(text="🟡 BACKGROUND CANVAS:"))
            content_parts.append(types.Part(
                inline_data=types.Blob(
                    mime_type='image/png' if background_path.endswith('.png') else 'image/jpeg', 
                    data=bg_bytes
                )
            ))
            
            # Image 3: ANGLE
            content_parts.append(types.Part(text="🟢 ANGLE REFERENCE:"))
            content_parts.append(types.Part(
                inline_data=types.Blob(
                    mime_type='image/jpeg', 
                    data=angle_bytes
                )
            ))
            
            # Prompt
            content_parts.append(types.Part(text=enhanced_prompt))
            
            print("DEBUG: Calling Gemini API (v2 SDK)...")
            
            # Use 'generate_content' with 'response_modalities=["IMAGE"]' as per reference
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[types.Content(role='user', parts=content_parts)],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"], # Request IMAGE output
                    temperature=0.7,
                    top_k=50,
                    top_p=0.95
                )
            )
            
            # 4. Process Response
            # Look for image in parts
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        print("DEBUG: Image received!")
                        image_bytes = part.inline_data.data
                        
                        generated_filename = f"gen_{int(time.time())}.jpg"
                        output_path = os.path.join("static", "generated", generated_filename)
                        
                        # Ensure the directory exists before saving
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
                        img = Image.open(BytesIO(image_bytes))
                        img.save(output_path)
                        return f"/static/generated/{generated_filename}"
            
            print(f"DEBUG: No image found in response. Text: {response.text}")
            # Raise error if no image
            raise Exception("No image returned by model")

        except Exception as e:
            print(f"CRITICAL ERROR in generation: {e}")
            import traceback
            traceback.print_exc()
            return "https://placehold.co/600x400?text=Generation+Failed+Check+Logs"
