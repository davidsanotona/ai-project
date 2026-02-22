# 🇨🇳 GenAI Mandarin HSK Learner Translation
Fine-tuned Transformer Model for HSK-Aligned Language Translation
## Executive Summary
This project demonstrates the application of Generative AI in education by fine-tuning a transformer-based model for Mandarin-to-English translation. Specifically, the model is aligned with the HSK (Hanyu Shuiping Kaoshi) curriculum, ensuring that the vocabulary and grammatical structures remain appropriate for specific learner levels.
## Technical Methodology
- Utilized existing fine-tuned Hugging Face Transformers (e.g., Helsinki-NLP/opus-mt-zh-en), downloaded offline.
- Domain Tuning: Performed domain-specific fine-tuning focused on HSK 1-6 vocabulary lists.
- Performance: Evaluated translation accuracy using the BLEU (Bilingual Evaluation Understudy) score.
- Pipeline: Integrated document-level translation for HSK learning materials.

## caveat
- model is developed with Helsinki-NLP/opus-mt-zh-en downloaded locally, you need to install it on your own
