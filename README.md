# MasterPiecer

1. Scrap kinopoisk.ru for synopses of differently rated movies.
2. Use GPT-2 to generate new synopses based on scrapped corpus.
3. Train BERT to rate movies by their synopses using scraped data.
4. Use trained BERT to rate synopses generated by GPT-2.
5. Choose several top-rated synopses.
6. ????????????????????
7. PROFIT!

---

## Scraping

Used TOR with [torpy](https://github.com/torpyorg/torpy/) package to avoid banning.
See scraping/scraping_tor.py

---

## GPT-2 fine-tuning

Used GPT-2 pretrained on russian corpus
by [Mikhail Grankin](https://github.com/mgrankin),
see [ru_transformers](https://github.com/mgrankin/ru_transformers).
Code for fine-tuning can be found in notebooks/generator_train.ipynb,
it can be easily adopted to any other corpus.
Code for generating samples of text from trained model can be
found in notebooks/generator.ipynb

---

## BERT training for rating

BERT was trained on google collab, see notebooks/rater_training.ipynb for code.
Inference code can be found in noteboooks/rating.ipynb.

---

### Technical requirements

Everything, but BERT training, was done on a laptop with
NVIDIA 1060 GPU with 6 Gb memory. BERT training was done with google collab
using Tesla P4 GPU.