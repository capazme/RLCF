import argparse
import json
import os
from sqlalchemy.orm import Session
from . import models
from .database import SessionLocal
from .models import TaskType

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SFT (Supervised Fine-Tuning) Formatters ---

def format_sft_summarization(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # SFT for summarization: Instruction + Document -> Revised Summary
    if not task.input_data or "document" not in task.input_data:
        return None
    if not feedback.feedback_data or "revised_summary" not in feedback.feedback_data:
        return None
    
    instruction = "Summarize the following document accurately and concisely."
    return {
        "instruction": instruction,
        "input": task.input_data["document"],
        "output": feedback.feedback_data["revised_summary"]
    }

def format_sft_classification(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # SFT for classification: Text + Unit -> Validated Labels
    if not task.input_data or "text" not in task.input_data or "unit" not in task.input_data:
        return None
    if not feedback.feedback_data or "validated_labels" not in feedback.feedback_data:
        return None
    
    instruction = f"Classify the following text unit: {task.input_data["unit"]}"
    return {
        "instruction": instruction,
        "input": task.input_data["text"],
        "output": ", ".join(feedback.feedback_data["validated_labels"])
    }

def format_sft_qa(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # SFT for QA: Context + Question -> Validated Answer
    if not task.input_data or "context" not in task.input_data or "question" not in task.input_data:
        return None
    if not feedback.feedback_data or "validated_answer" not in feedback.feedback_data:
        return None
    
    instruction = f"Answer the following question based on the provided context: {task.input_data["question"]}"
    return {
        "instruction": instruction,
        "input": task.input_data["context"],
        "output": feedback.feedback_data["validated_answer"]
    }

def format_sft_prediction(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # SFT for Prediction: Facts -> Chosen Outcome
    if not task.input_data or "facts" not in task.input_data:
        return None
    if not feedback.feedback_data or "chosen_outcome" not in feedback.feedback_data:
        return None
    
    instruction = "Predict the outcome based on the given facts."
    return {
        "instruction": instruction,
        "input": task.input_data["facts"],
        "output": feedback.feedback_data["chosen_outcome"]
    }

def format_sft_nli(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # SFT for NLI: Premise + Hypothesis -> Chosen Label
    if not task.input_data or "premise" not in task.input_data or "hypothesis" not in task.input_data:
        return None
    if not feedback.feedback_data or "chosen_label" not in feedback.feedback_data:
        return None
    
    instruction = f"Determine the relationship between the premise and hypothesis (entailment, contradiction, or neutral). Premise: {task.input_data["premise"]}"
    return {
        "instruction": instruction,
        "input": task.input_data["hypothesis"],
        "output": feedback.feedback_data["chosen_label"]
    }

def format_sft_ner(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # SFT for NER: Tokens -> Validated Tags
    if not task.input_data or "tokens" not in task.input_data:
        return None
    if not feedback.feedback_data or "validated_tags" not in feedback.feedback_data:
        return None
    
    instruction = "Identify and tag named entities in the following sequence of tokens."
    return {
        "instruction": instruction,
        "input": " ".join(task.input_data["tokens"]),
        "output": " ".join(feedback.feedback_data["validated_tags"])
    }

def format_sft_drafting(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # SFT for Drafting: Source + Instruction -> Revised Target
    if not task.input_data or "source" not in task.input_data or "instruction" not in task.input_data:
        return None
    if not feedback.feedback_data or "revised_target" not in feedback.feedback_data:
        return None
    
    instruction = f"Revise the following text based on the instruction: {task.input_data["instruction"]}"
    return {
        "instruction": instruction,
        "input": task.input_data["source"],
        "output": feedback.feedback_data["revised_target"]
    }

SFT_FORMATTERS = {
    TaskType.SUMMARIZATION: format_sft_summarization,
    TaskType.CLASSIFICATION: format_sft_classification,
    TaskType.QA: format_sft_qa,
    TaskType.PREDICTION: format_sft_prediction,
    TaskType.NLI: format_sft_nli,
    TaskType.NER: format_sft_ner,
    TaskType.DRAFTING: format_sft_drafting,
}

# --- Preference (RLHF) Formatters ---

def format_preference_drafting(task: models.LegalTask, response: models.Response, feedback: models.Feedback) -> dict:
    # Preference for drafting: Source + Instruction -> Chosen (revised_target) vs Rejected (original target)
    if not task.input_data or "source" not in task.input_data or "instruction" not in task.input_data:
        return None
    if not feedback.feedback_data or "revised_target" not in feedback.feedback_data or "rating" not in feedback.feedback_data:
        return None
    
    # Assuming original target is in response.output_data["target"]
    original_target = response.output_data.get("target")
    if not original_target:
        return None

    prompt = f"Revise the following text based on the instruction: {task.input_data["instruction"]}\nSource: {task.input_data["source"]}"
    
    if feedback.feedback_data["rating"] == "better":
        return {"prompt": prompt, "chosen": feedback.feedback_data["revised_target"], "rejected": original_target}
    elif feedback.feedback_data["rating"] == "worse":
        return {"prompt": prompt, "chosen": original_target, "rejected": feedback.feedback_data["revised_target"]}
    return None

# Add more preference formatters as needed
PREFERENCE_FORMATTERS = {
    TaskType.DRAFTING: format_preference_drafting,
}

# --- Main Export Logic ---

def export_dataset(task_type: TaskType, export_format: str, output_file: str):
    db_gen = get_db()
    db = next(db_gen) # Get the session

    query = db.query(models.LegalTask).filter(models.LegalTask.task_type == task_type.value)
    tasks = query.all()

    exported_records = []

    for task in tasks:
        # Get the AI-generated response for this task
        response = db.query(models.Response).filter(models.Response.task_id == task.id).first()
        if not response:
            continue

        # Get all feedback for this response
        feedbacks = db.query(models.Feedback).filter(models.Feedback.response_id == response.id).all()
        
        for feedback in feedbacks:
            record = None
            if export_format == "sft":
                formatter = SFT_FORMATTERS.get(task_type)
                if formatter:
                    record = formatter(task, response, feedback)
            elif export_format == "preference":
                formatter = PREFERENCE_FORMATTERS.get(task_type)
                if formatter:
                    record = formatter(task, response, feedback)
            
            if record:
                exported_records.append(record)
    
    with open(output_file, "w") as f:
        for record in exported_records:
            f.write(json.dumps(record) + "\n")
    
    print(f"Exported {len(exported_records)} records to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export RLCF data to fine-tuning datasets.")
    parser.add_argument("--task-type", type=str, required=True, choices=[t.value for t in TaskType], help="Type of task to export.")
    parser.add_argument("--format", type=str, required=True, choices=["sft", "preference"], help="Export format (sft or preference).")
    parser.add_argument("--output-file", type=str, required=True, help="Output .jsonl file path.")
    
    args = parser.parse_args()

    try:
        task_type_enum = TaskType(args.task_type)
        export_dataset(task_type_enum, args.format, args.output_file)
    except ValueError as e:
        print(f"Error: {e}")
        parser.print_help()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
