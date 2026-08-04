from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

print("Chargement du modèle CLIP...")
_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
print("Modèle CLIP prêt.")

# Description textuelle attendue pour chaque catégorie d'habitude
CATEGORY_PROMPTS = {
    "lecture": "a photo of a person reading a book",
    "sport": "a photo of a person exercising or doing sport",
    "santé": "a photo of healthy food, medicine, or a health related item",
    "méditation": "a photo of a person meditating or doing yoga",
    "productivité": "a photo of a desk, laptop, or someone working",
    "finance": "a photo of money, a bank app, or a budget spreadsheet",
    "apprentissage": "a photo of studying, a course, or learning material",
    "sommeil": "a photo of a bed or someone sleeping",
    "alimentation": "a photo of a healthy meal or food preparation",
    "social": "a photo of people together or a social gathering",
    "créativité": "a photo of art, drawing, or a creative project",
}

DEFAULT_PROMPT = "a photo related to a personal habit or activity"


def verify_photo(image_path: str, category: str, threshold: float = 0.25):
    """
    Analyse une image et vérifie si elle correspond à la catégorie de l'habitude.
    Retourne (ai_verified: bool, confidence_score: float)
    """
    expected_prompt = CATEGORY_PROMPTS.get((category or "").lower(), DEFAULT_PROMPT)

    # On compare avec quelques prompts négatifs pour calibrer le score
    candidate_prompts = [
        expected_prompt,
        "a random unrelated photo",
        "a screenshot or a blank image",
    ]

    image = Image.open(image_path).convert("RGB")
    inputs = _processor(text=candidate_prompts, images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        outputs = _model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0]

    score = probs[0].item()  # probabilité que ce soit le prompt attendu
    verified = score >= threshold

    return verified, round(score, 3)


if __name__ == "__main__":
    # Test rapide avec une image factice
    test_img = Image.new("RGB", (224, 224), color="white")
    test_img.save("test_image.jpg")
    verified, score = verify_photo("test_image.jpg", "sport")
    print(f"Vérifié: {verified}, Score: {score}")