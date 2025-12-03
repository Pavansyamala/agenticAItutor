from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import os

model_name = "mistralai/Mistral-7B-Instruct-v0.2"
save_path = "./saved_mistral_7b"

# Load normally the first time
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)

# Save model + tokenizer to local folder
if not os.path.exists(save_path):
    tokenizer.save_pretrained(save_path)
    model.save_pretrained(save_path)
    print(f"Saved Mistral locally at: {save_path}")
else:
    print("Model already saved — skipping save")

generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512,
    do_sample=False,
    temperature=0.0
)

print("Mistral loaded — ready for local inference!")
