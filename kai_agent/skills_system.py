"""
Hermes-inspired self-improving skills system for Kai.
Provides procedural memory, skill creation, and autonomous improvement.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import re


@dataclass
class Skill:
    """A learnable, improvable skill with procedural memory"""
    id: str
    name: str
    description: str
    category: str
    complexity: float = 1.0  # 0.0 to 10.0
    confidence: float = 0.5  # 0.0 to 1.0
    success_rate: float = 0.0
    usage_count: int = 0
    last_used: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Learning data
    successful_executions: List[Dict] = field(default_factory=list)
    failed_executions: List[Dict] = field(default_factory=list)
    learned_patterns: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)

    # Procedural memory
    steps: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    variations: Dict[str, List[str]] = field(default_factory=dict)

    def update_success(self, execution_data: Dict):
        """Update skill metrics after successful execution"""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        self.successful_executions.append(execution_data)
        self._recalculate_metrics()

    def update_failure(self, execution_data: Dict):
        """Update skill metrics after failed execution"""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        self.failed_executions.append(execution_data)
        self._recalculate_metrics()

    def _recalculate_metrics(self):
        """Recalculate confidence and success rate"""
        total_attempts = len(self.successful_executions) + len(self.failed_executions)
        if total_attempts > 0:
            self.success_rate = len(self.successful_executions) / total_attempts

        # Confidence increases with usage and success rate
        usage_factor = min(1.0, self.usage_count / 10.0)  # 10 uses for full confidence
        self.confidence = (self.success_rate * 0.7) + (usage_factor * 0.3)

    def learn_pattern(self, pattern: str):
        """Learn a new pattern or improvement"""
        if pattern not in self.learned_patterns:
            self.learned_patterns.append(pattern)

    def suggest_improvement(self, suggestion: str):
        """Add an improvement suggestion"""
        if suggestion not in self.improvement_suggestions:
            self.improvement_suggestions.append(suggestion)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Skill':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ExecutionTrajectory:
    """A complete execution trajectory for learning"""
    id: str
    skill_id: str
    start_time: str
    end_time: Optional[str] = None
    success: bool = False
    steps: List[Dict] = field(default_factory=list)
    context: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    learned_insights: List[str] = field(default_factory=list)

    def add_step(self, step_name: str, step_data: Dict):
        """Add an execution step"""
        self.steps.append({
            'name': step_name,
            'timestamp': datetime.now().isoformat(),
            'data': step_data
        })

    def complete(self, success: bool, errors: List[str] = None):
        """Mark trajectory as complete"""
        self.end_time = datetime.now().isoformat()
        self.success = success
        if errors:
            self.errors.extend(errors)


class KaiSkillsSystem:
    """
    Hermes-inspired skills system with procedural memory and self-improvement.
    Provides autonomous skill creation, improvement, and cross-session learning.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.skills_dir = workspace / "skills"
        self.trajectories_dir = workspace / "trajectories"
        self.skills_dir.mkdir(exist_ok=True)
        self.trajectories_dir.mkdir(exist_ok=True)

        self.skills: Dict[str, Skill] = {}
        self.active_trajectories: Dict[str, ExecutionTrajectory] = {}

        # Load existing skills
        self._load_skills()

    def _load_skills(self):
        """Load all skills from disk"""
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skill = Skill.from_dict(skill_data)
                    self.skills[skill.id] = skill
            except Exception as e:
                print("Failed to load skill {}: {}".format(skill_file, e))

    def _save_skill(self, skill: Skill):
        """Save a skill to disk"""
        skill_file = self.skills_dir / "{}.json".format(skill.id)
        try:
            with open(skill_file, 'w', encoding='utf-8') as f:
                json.dump(skill.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Failed to save skill {}: {}".format(skill.id, e))

    def create_skill_from_trajectory(self, trajectory: ExecutionTrajectory) -> Optional[Skill]:
        """Create a new skill from a successful trajectory"""
        if not trajectory.success or len(trajectory.steps) < 3:
            return None

        # Generate skill name from trajectory context
        skill_name = self._generate_skill_name(trajectory)

        # Check if similar skill already exists
        existing_skill = self.find_similar_skill(skill_name)
        if existing_skill:
            # Improve existing skill instead
            self.improve_skill_from_trajectory(existing_skill, trajectory)
            return existing_skill

        # Create new skill
        skill = Skill(
            id=self._generate_skill_id(skill_name),
            name=skill_name,
            description="Autonomously learned skill: {}".format(skill_name),
            category=self._categorize_skill(trajectory),
            complexity=len(trajectory.steps) / 10.0,  # Rough complexity estimate
            steps=[step['name'] for step in trajectory.steps],
            learned_patterns=trajectory.learned_insights
        )

        # Add successful execution
        execution_data = {
            'trajectory_id': trajectory.id,
            'steps_count': len(trajectory.steps),
            'duration': self._calculate_duration(trajectory),
            'context': trajectory.context
        }
        skill.update_success(execution_data)

        self.skills[skill.id] = skill
        self._save_skill(skill)

        print("[+] Created new skill: {} (ID: {})".format(skill.name, skill.id))
        return skill

    def _generate_skill_name(self, trajectory: ExecutionTrajectory) -> str:
        """Generate a descriptive name for the skill"""
        # Extract key actions from steps
        actions = [step['name'] for step in trajectory.steps[:5]]  # First 5 steps

        # Look for common patterns
        if any('scan' in action.lower() for action in actions):
            return "Network Scanning and Analysis"
        elif any('search' in action.lower() or 'find' in action.lower() for action in actions):
            return "Information Search and Retrieval"
        elif any('file' in action.lower() or 'read' in action.lower() for action in actions):
            return "File Operations and Analysis"
        elif any('web' in action.lower() or 'browser' in action.lower() for action in actions):
            return "Web Interaction and Automation"
        else:
            # Generic name based on first and last action
            first_action = actions[0] if actions else "Task"
            return "{} Workflow".format(first_action.title())

    def _generate_skill_id(self, name: str) -> str:
        """Generate unique skill ID"""
        base_id = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        counter = 1
        skill_id = base_id

        while skill_id in self.skills:
            skill_id = "{}_{}".format(base_id, counter)
            counter += 1

        return skill_id

    def _categorize_skill(self, trajectory: ExecutionTrajectory) -> str:
        """Categorize skill based on trajectory content"""
        actions = ' '.join([step['name'] for step in trajectory.steps]).lower()

        categories = {
            'security': ['scan', 'pentest', 'security', 'nmap', 'vulnerability'],
            'web': ['browser', 'web', 'http', 'url', 'site'],
            'file': ['file', 'read', 'write', 'search', 'folder'],
            'system': ['system', 'process', 'memory', 'cpu', 'network'],
            'automation': ['task', 'workflow', 'automation', 'script'],
        }

        for category, keywords in categories.items():
            if any(keyword in actions for keyword in keywords):
                return category

        return 'general'

    def _calculate_duration(self, trajectory: ExecutionTrajectory) -> float:
        """Calculate trajectory duration in seconds"""
        if not trajectory.end_time:
            return 0.0

        try:
            start = datetime.fromisoformat(trajectory.start_time)
            end = datetime.fromisoformat(trajectory.end_time)
            return (end - start).total_seconds()
        except:
            return 0.0

    def find_similar_skill(self, skill_name: str) -> Optional[Skill]:
        """Find a similar existing skill"""
        skill_name_lower = skill_name.lower()

        for skill in self.skills.values():
            if skill.name.lower() == skill_name_lower:
                return skill

            # Check for similar names (simple fuzzy matching)
            if self._similarity_score(skill.name.lower(), skill_name_lower) > 0.7:
                return skill

        return None

    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity score"""
        words1 = set(str1.split())
        words2 = set(str2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def improve_skill_from_trajectory(self, skill: Skill, trajectory: ExecutionTrajectory):
        """Improve existing skill using trajectory data"""
        # Add successful execution
        execution_data = {
            'trajectory_id': trajectory.id,
            'steps_count': len(trajectory.steps),
            'duration': self._calculate_duration(trajectory),
            'context': trajectory.context,
            'learned_patterns': trajectory.learned_insights
        }
        skill.update_success(execution_data)

        # Learn new patterns
        for insight in trajectory.learned_insights:
            skill.learn_pattern(insight)

        # Update steps if trajectory was more efficient
        if len(trajectory.steps) < len(skill.steps) and trajectory.success:
            skill.steps = [step['name'] for step in trajectory.steps]
            skill.suggest_improvement("Optimized to {} steps".format(len(trajectory.steps)))

        # Save improvements
        self._save_skill(skill)
        print("[+] Improved skill: {} (confidence: {:.2f})".format(skill.name, skill.confidence))

    def start_trajectory(self, skill_id: str, context: Dict = None) -> Optional[str]:
        """Start recording a new execution trajectory"""
        if skill_id not in self.skills:
            return None

        trajectory_id = "{}_{}".format(skill_id, int(time.time()))

        trajectory = ExecutionTrajectory(
            id=trajectory_id,
            skill_id=skill_id,
            start_time=datetime.now().isoformat(),
            context=context or {}
        )

        self.active_trajectories[trajectory_id] = trajectory
        return trajectory_id

    def record_step(self, trajectory_id: str, step_name: str, step_data: Dict):
        """Record a step in an active trajectory"""
        if trajectory_id in self.active_trajectories:
            self.active_trajectories[trajectory_id].add_step(step_name, step_data)

    def complete_trajectory(self, trajectory_id: str, success: bool, errors: List[str] = None, insights: List[str] = None):
        """Complete an execution trajectory and learn from it"""
        if trajectory_id not in self.active_trajectories:
            return

        trajectory = self.active_trajectories[trajectory_id]
        trajectory.complete(success, errors)

        if insights:
            trajectory.learned_insights.extend(insights)

        # Save trajectory
        self._save_trajectory(trajectory)

        # Learn from trajectory
        skill = self.skills.get(trajectory.skill_id)
        if skill:
            if success:
                execution_data = {
                    'trajectory_id': trajectory.id,
                    'steps_count': len(trajectory.steps),
                    'duration': self._calculate_duration(trajectory),
                    'context': trajectory.context,
                    'learned_patterns': trajectory.learned_insights
                }
                skill.update_success(execution_data)
            else:
                execution_data = {
                    'trajectory_id': trajectory.id,
                    'errors': trajectory.errors,
                    'failed_step': len(trajectory.steps)
                }
                skill.update_failure(execution_data)

            # Check if we can create a new skill from this trajectory
            if success and len(trajectory.steps) >= 3:
                new_skill = self.create_skill_from_trajectory(trajectory)
                if new_skill and new_skill != skill:
                    print("[+] Created related skill: {}".format(new_skill.name))

            self._save_skill(skill)

        # Clean up
        del self.active_trajectories[trajectory_id]

    def _save_trajectory(self, trajectory: ExecutionTrajectory):
        """Save trajectory to disk"""
        trajectory_file = self.trajectories_dir / "{}.json".format(trajectory.id)
        try:
            with open(trajectory_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(trajectory), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Failed to save trajectory {}: {}".format(trajectory.id, e))

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self.skills.get(skill_id)

    def list_skills(self, category: str = None) -> List[Skill]:
        """List all skills, optionally filtered by category"""
        skills = list(self.skills.values())

        if category:
            skills = [s for s in skills if s.category == category]

        # Sort by confidence and usage
        skills.sort(key=lambda s: (s.confidence, s.usage_count), reverse=True)
        return skills

    def search_skills(self, query: str) -> List[Skill]:
        """Search skills by name or description"""
        query_lower = query.lower()
        matching_skills = []

        for skill in self.skills.values():
            if (query_lower in skill.name.lower() or
                query_lower in skill.description.lower() or
                any(query_lower in pattern.lower() for pattern in skill.learned_patterns)):
                matching_skills.append(skill)

        return matching_skills

    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about the learning system"""
        total_skills = len(self.skills)
        total_trajectories = len(list(self.trajectories_dir.glob("*.json")))

        if total_skills == 0:
            return {'message': 'No skills learned yet'}

        avg_confidence = sum(s.confidence for s in self.skills.values()) / total_skills
        avg_success_rate = sum(s.success_rate for s in self.skills.values()) / total_skills
        total_usage = sum(s.usage_count for s in self.skills.values())

        # Most used skills
        most_used = sorted(self.skills.values(), key=lambda s: s.usage_count, reverse=True)[:5]

        # Recently learned skills
        recent_skills = sorted(self.skills.values(),
                             key=lambda s: s.created_at, reverse=True)[:3]

        return {
            'total_skills': total_skills,
            'total_trajectories': total_trajectories,
            'average_confidence': round(avg_confidence, 2),
            'average_success_rate': round(avg_success_rate, 2),
            'total_usage': total_usage,
            'most_used_skills': [
                {'name': s.name, 'usage_count': s.usage_count, 'confidence': round(s.confidence, 2)}
                for s in most_used
            ],
            'recent_skills': [
                {'name': s.name, 'created': s.created_at}
                for s in recent_skills
            ]
        }
