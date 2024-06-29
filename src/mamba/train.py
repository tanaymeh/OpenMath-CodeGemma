import torch

from mamba_ssm.models.mixer_seq_simple import MambaLMHeadModel
from transformers import AutoTokenizer, TrainingArguments

from data import MambaChatDataset, mamba_chat_collate_fn
from trainer import MambaTrainer

from functools import partial

import click


@click.command()
@click.option(
    "--model",
    default="state-spaces/mamba2-1.3b",
    help="Mamba Model to fine-tune. Must be non-HF",
)
@click.option("--tokenizer", default="EleutherAI/gpt-neox-20b", help="Tokenizer to use")
@click.option(
    "--data_path",
    default="data/train_openmath_data.jsonl",
    help="Path of the JSON data file to use",
)
@click.option("--num_epochs", default=2, help="Number of epochs to train the model for")
@click.option("--optim", default="adamw_torch", help="Learning rate")
@click.option("--lr", default=1e-5, help="Learning rate")
@click.option("--train_bs", default=16, help="Training batch size")
@click.option("--grad_accum", default=1, help="Gradient accumulation steps")
@click.option("--max_length", default=2048, help="Maximum context length of the model")
def run(
    model,
    tokenizer,
    data_path,
    num_epochs,
    optim,
    lr,
    train_bs,
    grad_accum,
    max_length,
):
    # Define model, tokenizer and chat template
    model = MambaLMHeadModel.from_pretrained(model, dtype=torch.bfloat16, device="cuda")
    tokenizer = AutoTokenizer.from_pretrained(tokenizer)

    tokenizer.eos_token = "<|endoftext|>"
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.chat_template = AutoTokenizer.from_pretrained(
        "HuggingFaceH4/zephyr-7b-beta"
    ).chat_template

    # Define the dataset and the partial collate fn
    train_ds = MambaChatDataset(
        data_path, tokenizer.chat_template, tokenizer, max_length
    )
    collate_fn = partial(mamba_chat_collate_fn, pad_token_id=tokenizer.pad_token_id)

    # Define the trainer
    trainer = MambaTrainer(
        model=model,
        train_dataset=train_ds,
        tokenizer=tokenizer,
        args=TrainingArguments(
            learning_rate=lr,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=train_bs,
            gradient_accumulation_steps=grad_accum,
            optim=optim,
            output_dir="models/mamba2-1.3b",
            logging_steps=5,
            save_steps=500,
            report_to="none",
        ),
        data_collator=collate_fn,
    )

    # Train the model
    trainer.train()

    # Save the model
    trainer.save_model("models/mamba2-1.3b")


if __name__ == "__main__":
    run()
