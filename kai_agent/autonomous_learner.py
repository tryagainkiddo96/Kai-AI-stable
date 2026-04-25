"""
Hermes-inspired autonomous skill creation system for Kai.
Automatically creates and improves skills from complex task executions.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from kai_agent.skills_system import KaiSkillsSystem, ExecutionTrajectory, Skill


@dataclass
class TaskObservation:
    """Observation of a task execution for skill learning"""
    task_id: str
    start_time: str
    user_intent: str
    steps_executed: List[Dict] = field(default_factory=list)
    tools_used: Set[str] = field(default_factory=set)
    success: bool = False
    complexity_score: float = 1.0
    learned_patterns: List[str] = field(default_factory=list)

    def add_step(self, step_name: str, tool_used: str = None, step_data: Dict = None):
        """Add a step to the observation"""
        self.steps_executed.append({
            'name': step_name,
            'tool': tool_used,
            'timestamp': datetime.now().isoformat(),
            'data': step_data or {}
        })

        if tool_used:
            self.tools_used.add(tool_used)

    def complete(self, success: bool):
        """Mark task as complete"""
        self.success = success

        # Calculate complexity based on steps and tools used
        self.complexity_score = len(self.steps_executed) * 0.5 + len(self.tools_used) * 0.3

        # Minimum complexity threshold for skill creation
        if self.complexity_score < 2.0:
            self.complexity_score = 1.0


class AutonomousSkillLearner:
    """
    Hermes-inspired autonomous skill creation and improvement system.
    Watches task executions and creates skills from successful complex workflows.
    """

    def __init__(self, workspace: Path, skills_system: KaiSkillsSystem):
        self.workspace = workspace
        self.skills_system = skills_system
        self.active_observations: Dict[str, TaskObservation] = {}
        self.learning_threshold = 3.0  # Minimum complexity for skill creation
        self.min_steps_for_skill = 3  # Minimum steps for skill creation

    def start_observing_task(self, task_id: str, user_intent: str) -> str:
        """Start observing a task execution"""
        observation = TaskObservation(
            task_id=task_id,
            start_time=datetime.now().isoformat(),
            user_intent=user_intent
        )

        self.active_observations[task_id] = observation
        return task_id

    def record_task_step(self, task_id: str, step_name: str, tool_used: str = None,
                        step_data: Dict = None):
        """Record a step in a task execution"""
        if task_id in self.active_observations:
            self.active_observations[task_id].add_step(step_name, tool_used, step_data)

    def complete_task_observation(self, task_id: str, success: bool,
                                learned_patterns: List[str] = None):
        """Complete task observation and potentially create a skill"""
        if task_id not in self.active_observations:
            return

        observation = self.active_observations[task_id]
        observation.complete(success)

        if learned_patterns:
            observation.learned_patterns.extend(learned_patterns)

        # Check if this task warrants skill creation
        if self._should_create_skill(observation):
            skill = self._create_skill_from_observation(observation)
            if skill:
                print(f"[+] Autonomously created skill: {skill.name}")
                return skill

        # Clean up
        del self.active_observations[task_id]
        return None

    def _should_create_skill(self, observation: TaskObservation) -> bool:
        """Determine if an observation warrants skill creation"""
        if not observation.success:
            return False

        if len(observation.steps_executed) < self.min_steps_for_skill:
            return False

        if observation.complexity_score < self.learning_threshold:
            return False

        # Check if similar skill already exists and is well-established
        similar_skill = self.skills_system.find_similar_skill(
            self._generate_skill_name_from_observation(observation)
        )

        if similar_skill and similar_skill.confidence > 0.8:
            # Skill exists and is confident, just improve it instead
            return False

        return True

    def _create_skill_from_observation(self, observation: TaskObservation) -> Optional[Skill]:
        """Create a new skill from a task observation"""

        # Convert observation to trajectory
        trajectory = ExecutionTrajectory(
            id=f"auto_{observation.task_id}_{int(time.time())}",
            skill_id="",  # Will be set when skill is created
            start_time=observation.start_time,
            context={
                'user_intent': observation.user_intent,
                'tools_used': list(observation.tools_used),
                'complexity': observation.complexity_score
            }
        )

        # Add steps to trajectory
        for step in observation.steps_executed:
            trajectory.add_step(step['name'], step)

        # Complete trajectory
        trajectory.complete(True, [])
        trajectory.learned_insights.extend(observation.learned_patterns)

        # Create skill from trajectory
        skill = self.skills_system.create_skill_from_trajectory(trajectory)

        if skill:
            # Add additional metadata
            skill.suggest_improvement(f"Autonomously learned from task: {observation.user_intent}")
            self.skills_system._save_skill(skill)

        return skill

    def _generate_skill_name_from_observation(self, observation: TaskObservation) -> str:
        """Generate a skill name from task observation"""
        intent = observation.user_intent.lower()

        # Extract key actions from steps
        actions = [step['name'] for step in observation.steps_executed]

        # Try to create meaningful name based on intent and actions
        if 'scan' in intent or any('scan' in action.lower() for action in actions):
            return "Comprehensive Security Scanning"
        elif 'search' in intent or any('search' in action.lower() for action in actions):
            return "Advanced Information Retrieval"
        elif 'analyze' in intent or any('analyze' in action.lower() for action in actions):
            return "Deep Content Analysis"
        elif 'organize' in intent or any('organize' in action.lower() for action in actions):
            return "File and Data Organization"
        elif 'monitor' in intent or any('monitor' in action.lower() for action in actions):
            return "System Monitoring and Alerting"
        else:
            # Use first step as basis
            first_action = actions[0] if actions else "Task"
            return f"{first_action.title()} Automation"

    def improve_existing_skills(self):
        """Periodically improve existing skills based on accumulated data"""
        skills = self.skills_system.list_skills()

        for skill in skills:
            if skill.usage_count >= 5:  # Only improve well-used skills
                improvements = self._analyze_skill_improvements(skill)
                if improvements:
                    for improvement in improvements:
                        skill.suggest_improvement(improvement)
                    self.skills_system._save_skill(skill)
                    print(f"[+] Improved skill: {skill.name} ({len(improvements)} suggestions)")

    def _analyze_skill_improvements(self, skill: Skill) -> List[str]:
        """Analyze a skill and suggest improvements"""
        improvements = []

        # Check success rate
        if skill.success_rate < 0.7 and skill.usage_count >= 10:
            improvements.append("Improve success rate - consider alternative approaches for failed executions")

        # Check if skill is too complex
        if len(skill.steps) > 10 and skill.confidence < 0.6:
            improvements.append("Consider breaking down into smaller sub-skills for better reliability")

        # Check for common failure patterns
        failed_executions = [exec for exec in skill.failed_executions if exec.get('errors')]
        if failed_executions:
            error_patterns = {}
            for failed_exec in failed_executions:
                errors = failed_exec.get('errors', [])
                for error in errors:
                    error_patterns[error] = error_patterns.get(error, 0) + 1

            if error_patterns:
                most_common_error = max(error_patterns.items(), key=lambda x: x[1])
                improvements.append(f"Address common failure: {most_common_error[0]}")

        # Suggest optimizations based on successful executions
        successful_executions = skill.successful_executions
        if len(successful_executions) >= 3:
            durations = [exec.get('duration', 0) for exec in successful_executions if exec.get('duration')]
            if durations:
                avg_duration = sum(durations) / len(durations)
                if avg_duration > 60:  # Over 1 minute
                    improvements.append("Consider optimizing for speed - execution is taking too long")

        return improvements

    def get_learning_status(self) -> Dict[str, Any]:
        """Get status of autonomous learning system"""
        active_tasks = len(self.active_observations)
        total_skills_created = len(self.skills_system.list_skills())

        # Count skills created autonomously
        autonomous_skills = [s for s in self.skills_system.list_skills()
                           if any('Autonomously learned' in imp for imp in s.improvement_suggestions)]

        recent_activity = []
        for task_id, observation in list(self.active_observations.items())[:5]:
            recent_activity.append({
                'task_id': task_id,
                'intent': observation.user_intent,
                'steps': len(observation.steps_executed),
                'tools': list(observation.tools_used),
                'complexity': round(observation.complexity_score, 2)
            })

        return {
            'active_observations': active_tasks,
            'total_skills': total_skills_created,
            'autonomous_skills': len(autonomous_skills),
            'learning_threshold': self.learning_threshold,
            'recent_activity': recent_activity,
            'system_status': 'active' if active_tasks > 0 else 'idle'
        }

    def nudge_learning(self):
        """Hermes-inspired 'nudge' to encourage learning from recent activity"""
        # This would be called periodically to encourage the system to learn
        # from recent conversations and task executions

        # Analyze recent trajectories for patterns
        trajectory_files = list(self.workspace.glob("trajectories/*.json"))
        recent_trajectories = []

        for traj_file in trajectory_files[-10:]:  # Last 10 trajectories
            try:
                with open(traj_file, 'r') as f:
                    data = json.load(f)
                    recent_trajectories.append(data)
            except:
                pass

        # Look for patterns in successful trajectories
        successful_trajectories = [t for t in recent_trajectories if t.get('success')]

        if len(successful_trajectories) >= 3:
            # Analyze for common patterns
            common_patterns = self._find_common_patterns(successful_trajectories)

            if common_patterns:
                print(f"[+] Learning nudge: Found {len(common_patterns)} common patterns in recent activity")

                # Create skills from patterns if they meet criteria
                for pattern in common_patterns:
                    if pattern['frequency'] >= 3 and pattern['avg_steps'] >= 3:
                        # This could warrant a new skill
                        print(f"[+] Pattern suggests potential skill: {pattern['description']}")

    def _find_common_patterns(self, trajectories: List[Dict]) -> List[Dict]:
        """Find common patterns in trajectories"""
        patterns = {}

        for trajectory in trajectories:
            steps = trajectory.get('steps', [])
            step_names = [step.get('name', '') for step in steps]

            # Create pattern signature
            signature = ' -> '.join(step_names[:5])  # First 5 steps

            if signature not in patterns:
                patterns[signature] = {
                    'signature': signature,
                    'trajectories': [],
                    'total_steps': 0,
                    'frequency': 0
                }

            patterns[signature]['trajectories'].append(trajectory['id'])
            patterns[signature]['total_steps'] += len(steps)
            patterns[signature]['frequency'] += 1

        # Convert to list with averages
        pattern_list = []
        for pattern_data in patterns.values():
            if pattern_data['frequency'] >= 2:  # At least 2 occurrences
                avg_steps = pattern_data['total_steps'] / pattern_data['frequency']
                pattern_list.append({
                    'signature': pattern_data['signature'],
                    'frequency': pattern_data['frequency'],
                    'avg_steps': avg_steps,
                    'description': f"Pattern: {pattern_data['signature']} (avg {avg_steps:.1f} steps)"
                })

        return sorted(pattern_list, key=lambda x: x['frequency'], reverse=True)
