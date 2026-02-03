import torch

t = torch.tensor([1, 2, 3])
print(f"Iterating tensor: {[f'{x}' for x in t]}")
print(f"Iterating list: {[f'{x}' for x in t.tolist()]}")
