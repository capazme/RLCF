from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models
from collections import Counter, defaultdict
import numpy as np


async def calculate_professional_clustering_bias(
    db: AsyncSession, user_id: int, task_id: int
) -> float:
    """
    Calculate user bias as deviation from their professional group's consensus.

    Args:
        db (AsyncSession): Database session
        user_id (int): ID of the user to analyze
        task_id (int): ID of the task to analyze

    Returns:
        float: Bias score (1.0 if user disagrees with group, 0.0 otherwise)
    """
    # 1. Find user's professional group (e.g., 'Civil Law')
    result = await db.execute(
        select(models.Credential).where(
            models.Credential.user_id == user_id,
            models.Credential.type == "PROFESSIONAL_FIELD",
        )
    )
    user_credential = result.scalar_one_or_none()
    if not user_credential:
        return 0.0  # User has no defined professional group, cannot calculate bias

    professional_group = user_credential.value

    # 2. Find all feedback for that task given by users from the same group
    result = await db.execute(
        select(models.Feedback)
        .join(models.User)
        .join(models.Credential)
        .join(models.Response)
        .where(
            models.Credential.type == "PROFESSIONAL_FIELD",
            models.Credential.value == professional_group,
            models.Response.task_id == task_id,
        )
    )
    group_feedbacks = result.scalars().all()

    if (
        not group_feedbacks or len(group_feedbacks) < 2
    ):  # If no group or user is the only one
        return 0.0

    # 3. Calculate group consensus position
    position_counts = Counter(f.position for f in group_feedbacks)
    group_consensus_position = position_counts.most_common(1)[0][0]

    # 4. Find the specific user's position
    user_feedback = next((f for f in group_feedbacks if f.user_id == user_id), None)
    if not user_feedback:
        return 0.0

    # 5. Calculate bias
    bias_score = 0.0 if user_feedback.position == group_consensus_position else 1.0
    return bias_score


async def calculate_demographic_bias(db: AsyncSession, task_id: int) -> float:
    """
    Calculate demographic bias by analyzing correlation between demographic characteristics and positions taken.

    Args:
        db (AsyncSession): Database session
        task_id (int): ID of the task to analyze

    Returns:
        float: Demographic bias score (higher values indicate more bias)
    """
    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .where(models.Response.task_id == task_id)
    )
    feedbacks = result.scalars().all()

    # Group by demographic characteristics (e.g., experience)
    experience_groups = defaultdict(list)
    for fb in feedbacks:
        result = await db.execute(
            select(models.Credential).where(
                models.Credential.user_id == fb.user_id,
                models.Credential.type == "PROFESSIONAL_EXPERIENCE",
            )
        )
        exp_cred = result.scalar_one_or_none()

        if exp_cred:
            exp_years = float(exp_cred.value)
            if exp_years < 5:
                group = "junior"
            elif exp_years < 15:
                group = "mid"
            else:
                group = "senior"

            experience_groups[group].append(str(fb.feedback_data))

    # Calculate homogeneity within groups
    group_homogeneity_scores = []
    for group, positions in experience_groups.items():
        if len(positions) > 1:
            position_counts = Counter(positions)
            total = len(positions)
            homogeneity = max(position_counts.values()) / total
            group_homogeneity_scores.append(homogeneity)

    # High homogeneity = high demographic bias
    return np.mean(group_homogeneity_scores) if group_homogeneity_scores else 0.0


async def calculate_temporal_bias(db: AsyncSession, task_id: int) -> float:
    """
    Calculate temporal bias by analyzing how opinions change over time during evaluation.

    Args:
        db (AsyncSession): Database session
        task_id (int): ID of the task to analyze

    Returns:
        float: Temporal bias score (drift in opinions over time, normalized to [0,1])
    """
    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .where(models.Response.task_id == task_id)
        .order_by(models.Feedback.submitted_at)
    )
    feedbacks = result.scalars().all()

    if len(feedbacks) < 4:
        return 0.0

    # Split into first half and second half
    mid_point = len(feedbacks) // 2
    first_half = feedbacks[:mid_point]
    second_half = feedbacks[mid_point:]

    # Count positions in each half
    first_positions = Counter(str(fb.feedback_data) for fb in first_half)
    second_positions = Counter(str(fb.feedback_data) for fb in second_half)

    # Calculate drift as difference in distributions
    all_positions = set(first_positions.keys()) | set(second_positions.keys())

    drift_score = 0.0
    for pos in all_positions:
        first_freq = first_positions.get(pos, 0) / len(first_half)
        second_freq = second_positions.get(pos, 0) / len(second_half)
        drift_score += abs(first_freq - second_freq)

    return drift_score / 2  # Normalize to [0, 1]


async def calculate_geographic_bias(db: AsyncSession, task_id: int) -> float:
    """
    Calculate geographic bias if location data is available.

    Args:
        db (AsyncSession): Database session
        task_id (int): ID of the task to analyze

    Returns:
        float: Geographic bias score (using professional field as proxy for location)
    """
    # Placeholder - in production you would use real location data
    # For now, simulate using professional "field" as proxy
    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .where(models.Response.task_id == task_id)
    )
    feedbacks = result.scalars().all()

    field_positions = defaultdict(list)

    for fb in feedbacks:
        result = await db.execute(
            select(models.Credential).where(
                models.Credential.user_id == fb.user_id,
                models.Credential.type == "PROFESSIONAL_FIELD",
            )
        )
        field_cred = result.scalar_one_or_none()

        if field_cred:
            field_positions[field_cred.value].append(str(fb.feedback_data))

    # Calculate homogeneity by field
    field_homogeneity_scores = []
    for field, positions in field_positions.items():
        if len(positions) > 1:
            position_counts = Counter(positions)
            total = len(positions)
            homogeneity = max(position_counts.values()) / total
            field_homogeneity_scores.append(homogeneity)

    return np.mean(field_homogeneity_scores) if field_homogeneity_scores else 0.0


async def calculate_confirmation_bias(db: AsyncSession, task_id: int) -> float:
    """
    Calculate confirmation bias by analyzing if users tend to confirm their previous positions.

    Args:
        db (AsyncSession): Database session
        task_id (int): ID of the task to analyze

    Returns:
        float: Confirmation bias score (tendency to repeat previous positions)
    """
    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .where(models.Response.task_id == task_id)
    )
    feedbacks = result.scalars().all()

    confirmation_scores = []

    for fb in feedbacks:
        # Find previous feedback from the same user on similar tasks
        # First, get the task to access task_type
        result = await db.execute(
            select(models.LegalTask)
            .join(models.Response)
            .where(models.Response.id == fb.response_id)
        )
        task = result.scalar_one_or_none()

        if task:
            user_task_type = task.task_type
            result = await db.execute(
                select(models.Feedback)
                .join(models.Response)
                .join(models.LegalTask)
                .where(
                    models.Feedback.user_id == fb.user_id,
                    models.LegalTask.task_type == user_task_type,
                    models.Feedback.submitted_at < fb.submitted_at,
                )
            )
            previous_feedbacks = result.scalars().all()

            if previous_feedbacks:
                # Calculate similarity with previous positions
                current_position = str(fb.feedback_data)
                similar_previous = sum(
                    1
                    for prev_fb in previous_feedbacks
                    if str(prev_fb.feedback_data) == current_position
                )
                confirmation_score = similar_previous / len(previous_feedbacks)
                confirmation_scores.append(confirmation_score)

    return np.mean(confirmation_scores) if confirmation_scores else 0.0


async def calculate_anchoring_bias(db: AsyncSession, task_id: int) -> float:
    """
    Calculate anchoring bias by analyzing the influence of first responses on subsequent ones.

    Args:
        db (AsyncSession): Database session
        task_id (int): ID of the task to analyze

    Returns:
        float: Anchoring bias score (influence of early responses on later ones)
    """
    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .where(models.Response.task_id == task_id)
        .order_by(models.Feedback.submitted_at)
    )
    feedbacks = result.scalars().all()

    if len(feedbacks) < 5:
        return 0.0

    # Take the first 3 responses as "anchor"
    anchor_feedbacks = feedbacks[:3]
    subsequent_feedbacks = feedbacks[3:]

    # Calculate distribution of positions in the anchor
    anchor_positions = Counter(str(fb.feedback_data) for fb in anchor_feedbacks)
    anchor_dominant = anchor_positions.most_common(1)[0][0]

    # Calculate how many subsequent responses follow the anchor's dominant position
    subsequent_following_anchor = sum(
        1 for fb in subsequent_feedbacks if str(fb.feedback_data) == anchor_dominant
    )

    if not subsequent_feedbacks:
        return 0.0

    return subsequent_following_anchor / len(subsequent_feedbacks)


async def calculate_total_bias(db: AsyncSession, task_id: int) -> dict:
    """
    Calculate all types of bias and return a complete report.

    Args:
        db (AsyncSession): Database session
        task_id (int): ID of the task to analyze

    Returns:
        dict: Complete bias analysis report with individual bias scores and totals
    """
    b1 = await calculate_demographic_bias(db, task_id)

    # Get first user_id for professional clustering calculation
    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .where(models.Response.task_id == task_id)
    )
    first_feedback = result.scalars().first()
    user_id = first_feedback.user_id if first_feedback else 0

    b2 = await calculate_professional_clustering_bias(db, user_id, task_id)
    b3 = await calculate_temporal_bias(db, task_id)
    b4 = await calculate_geographic_bias(db, task_id)
    b5 = await calculate_confirmation_bias(db, task_id)
    b6 = await calculate_anchoring_bias(db, task_id)

    # Calculate total bias as Euclidean norm
    bias_components = [b1, b2, b3, b4, b5, b6]
    total_bias = np.sqrt(sum(b**2 for b in bias_components))

    return {
        "demographic_bias": round(b1, 3),
        "professional_clustering": round(b2, 3),
        "temporal_drift": round(b3, 3),
        "geographic_concentration": round(b4, 3),
        "confirmation_bias": round(b5, 3),
        "anchoring_bias": round(b6, 3),
        "total_bias_score": round(total_bias, 3),
        "bias_level": (
            "high" if total_bias > 1.0 else "medium" if total_bias > 0.5 else "low"
        ),
        "dominant_bias_types": sorted(
            [
                ("demographic", b1),
                ("professional", b2),
                ("temporal", b3),
                ("geographic", b4),
                ("confirmation", b5),
                ("anchoring", b6),
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:3],
    }


def generate_bias_mitigation_recommendations(bias_report: dict) -> list:
    """
    Generate recommendations to mitigate identified biases.

    Args:
        bias_report (dict): Bias analysis report containing individual bias scores

    Returns:
        list: List of mitigation recommendations with priority and implementation details
    """
    recommendations = []

    if bias_report["demographic_bias"] > 0.6:
        recommendations.append(
            {
                "type": "demographic",
                "priority": "high",
                "action": "Ensure diverse participation across experience levels",
                "implementation": "Set quotas for junior, mid-level, and senior participants",
            }
        )

    if bias_report["professional_clustering"] > 0.6:
        recommendations.append(
            {
                "type": "professional",
                "priority": "high",
                "action": "Cross-pollinate between professional fields",
                "implementation": "Require evaluation from at least 2 different specializations",
            }
        )

    if bias_report["temporal_drift"] > 0.4:
        recommendations.append(
            {
                "type": "temporal",
                "priority": "medium",
                "action": "Implement blind evaluation periods",
                "implementation": "Hide timestamps and previous responses during evaluation",
            }
        )

    if bias_report["confirmation_bias"] > 0.5:
        recommendations.append(
            {
                "type": "confirmation",
                "priority": "medium",
                "action": "Encourage devil's advocate participation",
                "implementation": "Assign 10-15% of evaluators as devil's advocates",
            }
        )

    if bias_report["anchoring_bias"] > 0.6:
        recommendations.append(
            {
                "type": "anchoring",
                "priority": "high",
                "action": "Randomize response presentation order",
                "implementation": "Show responses in random order to each evaluator",
            }
        )

    return recommendations


async def calculate_authority_correctness_correlation(db: AsyncSession) -> float:
    """
    Calculate Pearson correlation between users' authority scores and their aggregated correctness scores.

    Args:
        db (AsyncSession): Database session

    Returns:
        float: Correlation coefficient between authority and correctness scores
    """
    result = await db.execute(select(models.User))
    users = result.scalars().all()
    authority_scores = []
    correctness_scores = []

    for user in users:
        result = await db.execute(
            select(models.Feedback).where(models.Feedback.user_id == user.id)
        )
        user_feedbacks = result.scalars().all()
        if not user_feedbacks:
            continue

        # Aggregate correctness scores for the user
        total_correctness = sum(
            [
                fb.correctness_score
                for fb in user_feedbacks
                if fb.correctness_score is not None
            ]
        )
        num_correctness_scores = len(
            [fb for fb in user_feedbacks if fb.correctness_score is not None]
        )

        if num_correctness_scores > 0:
            avg_correctness = total_correctness / num_correctness_scores
            authority_scores.append(user.authority_score)
            correctness_scores.append(avg_correctness)

    if len(authority_scores) < 2:  # Need at least two data points for correlation
        return 0.0

    return np.corrcoef(authority_scores, correctness_scores)[0, 1]
