#!/usr/bin/env python3
"""
Pre-download ML model for Docker image build.
This script downloads the model during Docker build, so it's cached in the image.
"""
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_NAME = os.getenv("DEFAULT_MODEL", "unitary/toxic-bert")
CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./models_cache")

print(f"Downloading model: {MODEL_NAME}")
print(f"Cache directory: {CACHE_DIR}")

# Download tokenizer
print("Downloading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
print("Tokenizer downloaded successfully")

# Download model
print("Downloading model weights...")
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
print("Model downloaded successfully")

print(f"Model cached in: {CACHE_DIR}")
print("Download complete!")