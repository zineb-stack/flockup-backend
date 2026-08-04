from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

print("Chargement du modèle CLIP (première fois : téléchargement ~600MB)...")
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
print("Modèle chargé avec succès !")

# Test simple avec une image d'exemple (on va en créer une factice)
img = Image.new("RGB", (224, 224), color="white")

texts = ["a person reading a book", "a person exercising", "a cat"]
inputs = processor(text=texts, images=img, return_tensors="pt", padding=True)

with torch.no_grad():
    outputs = model(**inputs)
    logits_per_image = outputs.logits_per_image
    probs = logits_per_image.softmax(dim=1)

print("\nRésultats du test (image blanche factice) :")
for text, prob in zip(texts, probs[0]):
    print(f"  {text}: {prob.item():.2%}")

print("\n✅ CLIP fonctionne correctement !")