import sys
sys.path.append("src")

from transformers import GPT2Tokenizer, GPT2LMHeadModel
from yt_encoder import YTEncoder

import torch
import numpy as np

from pathlib import Path

PATH_TO_DATA = Path("data")
PATH_TO_MODELS = Path("models")


def choose_from_top(probs, n=5):
    ind = np.argpartition(probs, -n)[-n:]
    top_prob = probs[ind]
    top_prob = top_prob / np.sum(top_prob) # Normalize
    choice = np.random.choice(n, 1, p = top_prob)
    token_id = ind[choice][0]
    return int(token_id)


def generate_some_text(input_str, text_len = 250):

    cur_ids = torch.tensor(tokenizer.encode(input_str)).unsqueeze(0).long().to(device)

    model.eval()
    with torch.no_grad():

        for i in range(text_len):
            outputs = model(cur_ids, labels=cur_ids)
            loss, logits = outputs[:2]
            softmax_logits = torch.softmax(logits[0, -1], dim=0) #Take the first(only one) batch and the last predicted embedding
            next_token_id = choose_from_top(softmax_logits.to('cpu').numpy(), n=10) #Randomly(from the given probability distribution) choose the next word from the top n words
            cur_ids = torch.cat([cur_ids, torch.ones((1, 1)).long().to(device) * next_token_id], dim=1) # Add the last word

        output_list = list(cur_ids.squeeze().to('cpu').numpy())
        output_text = tokenizer.decode([output_list])
        print(output_text)


if __name__ == '__main__':

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tokenizer = YTEncoder.from_pretrained(str(PATH_TO_MODELS / "yt.model"))
    model = GPT2LMHeadModel.from_pretrained(str(PATH_TO_MODELS / "m_gpt_2/")).to(device)

    generate_some_text(" хм...фестиваль в сочи...киберсборная сельца ")
