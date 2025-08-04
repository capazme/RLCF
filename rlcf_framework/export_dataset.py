import argparse
import json
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


def format_sft_summarization(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for summarization: Instruction + Document -> Revised Summary
    # Assumes input_data and feedback_data are already validated by schemas
    instruction = "Summarize the following document accurately and concisely."
    return {
        "instruction": instruction,
        "input": task.input_data.get("document"),
        "output": feedback.feedback_data.get("revised_summary"),
    }


def format_sft_classification(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for classification: Text + Unit -> Validated Labels
    instruction = f"Classify the following text unit: {task.input_data.get("unit")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("text"),
        "output": ", ".join(feedback.feedback_data.get("validated_labels", [])),
    }


def format_sft_qa(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for QA: Context + Question -> Validated Answer
    instruction = f"Answer the following question based on the provided context: {task.input_data.get("question")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("context"),
        "output": feedback.feedback_data.get("validated_answer"),
    }


def format_sft_prediction(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for Prediction: Facts -> Chosen Outcome
    instruction = "Predict the outcome based on the given facts."
    return {
        "instruction": instruction,
        "input": task.input_data.get("facts"),
        "output": feedback.feedback_data.get("chosen_outcome"),
    }


def format_sft_nli(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for NLI: Premise + Hypothesis -> Chosen Label
    instruction = f"Determine the relationship between the premise and hypothesis (entailment, contradiction, or neutral). Premise: {task.input_data.get("premise")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("hypothesis"),
        "output": feedback.feedback_data.get("chosen_label"),
    }


def format_sft_ner(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for NER: Tokens -> Validated Tags
    instruction = "Identify and tag named entities in the following sequence of tokens."
    return {
        "instruction": instruction,
        "input": " ".join(task.input_data.get("tokens", [])),
        "output": " ".join(feedback.feedback_data.get("validated_tags", [])),
    }


def format_sft_drafting(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for Drafting: Source + Instruction -> Revised Target
    instruction = f"Revise the following text based on the instruction: {task.input_data.get("instruction")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("source"),
        "output": feedback.feedback_data.get("revised_target"),
    }


def format_sft_risk_spotting(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for risk spotting: Text -> Validated Labels and Severity
    instruction = (
        "Identify compliance risks in the following text and assign a severity score."
    )
    labels = feedback.feedback_data.get("validated_risk_labels", [])
    severity = feedback.feedback_data.get("validated_severity", 0)
    return {
        "instruction": instruction,
        "input": task.input_data.get("text"),
        "output": f"Risks: {', '.join(labels)}, Severity: {severity}",
    }


def format_sft_doctrine_application(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for doctrine application: Facts + Question -> Chosen Label
    instruction = f"Apply legal doctrine to answer the following question based on the facts: {task.input_data.get("question")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("facts"),
        "output": feedback.feedback_data.get("chosen_label"),
    }


SFT_FORMATTERS = {
    TaskType.SUMMARIZATION: format_sft_summarization,
    TaskType.CLASSIFICATION: format_sft_classification,
    TaskType.QA: format_sft_qa,
    TaskType.PREDICTION: format_sft_prediction,
    TaskType.NLI: format_sft_nli,
    TaskType.NER: format_sft_ner,
    TaskType.DRAFTING: format_sft_drafting,
    TaskType.RISK_SPOTTING: format_sft_risk_spotting,
    TaskType.DOCTRINE_APPLICATION: format_sft_doctrine_application,
}

# --- Preference (RLHF) Formatters ---


def format_preference_drafting(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # Preference for drafting: Source + Instruction -> Chosen (revised_target) vs Rejected (original target)
    # Assumes input_data and feedback_data are already validated by schemas
    original_target = response.output_data.get("target")
    if not original_target:
        return None

    prompt = f"Revise the following text based on the instruction: {task.input_data.get("instruction")}\nSource: {task.input_data.get("source")}"

    if feedback.feedback_data.get("rating") == "better":
        return {
            "prompt": prompt,
            "chosen": feedback.feedback_data.get("revised_target"),
            "rejected": original_target,
        }
    elif feedback.feedback_data.get("rating") == "worse":
        return {
            "prompt": prompt,
            "chosen": original_target,
            "rejected": feedback.feedback_data.get("revised_target"),
        }
    return None


# Add more preference formatters as needed
PREFERENCE_FORMATTERS = {
    TaskType.DRAFTING: format_preference_drafting,
}

# --- Main Export Logic ---


def export_dataset(task_type: TaskType, export_format: str, output_file: str):
    db_gen = get_db()
    db = next(db_gen)  # Get the session

    query = db.query(models.LegalTask).filter(
        models.LegalTask.task_type == task_type.value
    )
    tasks = query.all()

    exported_records = []

    for task in tasks:
        # Get the AI-generated response for this task
        response = (
            db.query(models.Response).filter(models.Response.task_id == task.id).first()
        )
        if not response:
            continue

        # Get all feedback for this response
        feedbacks = (
            db.query(models.Feedback)
            .filter(models.Feedback.response_id == response.id)
            .all()
        )

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
    parser = argparse.ArgumentParser(
        description="Export RLCF data to fine-tuning datasets."
    )
    parser.add_argument(
        "--task-type",
        type=str,
        required=True,
        choices=[t.value for t in TaskType],
        help="Type of task to export.",
    )
    parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["sft", "preference"],
        help="Export format (sft or preference).",
    )
    parser.add_argument(
        "--output-file", type=str, required=True, help="Output .jsonl file path."
    )

    args = parser.parse_args()

    try:
        task_type_enum = TaskType(args.task_type)
        export_dataset(task_type_enum, args.format, args.output_file)
    except ValueError as e:
        print(f"Error: {e}")
        parser.print_help()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
