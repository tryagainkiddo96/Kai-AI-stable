"""
Kai AI Learning System - Self-improving skills and memory
Closes the AI learning and memory gaps with procedural learning
"""

import json
import hashlib
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class LearnedSkill:
    """A skill that Kai has learned through experience"""
    id: str
    name: str
    description: str
    category: str
    confidence: float = 0.5  # 0.0 to 1.0
    usage_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Learning data
    successful_executions: List[Dict] = field(default_factory=list)
    failed_executions: List[Dict] = field(default_factory=list)
    learned_patterns: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)

    # Skill steps and prerequisites
    steps: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    variations: Dict[str, List[str]] = field(default_factory=dict)

    def record_success(self, execution_data: Dict):
        """Record a successful execution"""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        self.successful_executions.append(execution_data)
        self._update_metrics()

    def record_failure(self, execution_data: Dict):
        """Record a failed execution"""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        self.failed_executions.append(execution_data)
        self._update_metrics()

    def _update_metrics(self):
        """Update confidence and success rate"""
        total = len(self.successful_executions) + len(self.failed_executions)
        if total > 0:
            self.success_rate = len(self.successful_executions) / total
            # Confidence increases with usage and success
            usage_factor = min(1.0, self.usage_count / 10.0)
            self.confidence = (self.success_rate * 0.7) + (usage_factor * 0.3)

    def add_pattern(self, pattern: str):
        """Add a learned pattern"""
        if pattern not in self.learned_patterns:
            self.learned_patterns.append(pattern)

    def add_improvement(self, suggestion: str):
        """Add an improvement suggestion"""
        if suggestion not in self.improvement_suggestions:
            self.improvement_suggestions.append(suggestion)


@dataclass
class ConversationMemory:
    """A memory fragment from conversations"""
    id: str
    timestamp: str
    user_input: str
    kai_response: str
    context: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 1.0
    insights: List[str] = field(default_factory=list)
    session_id: str = "default"


class KaiLearningSystem:
    """
    Self-improving AI learning system for Kai.
    Provides skills acquisition, memory, and continuous improvement.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.skills_dir = workspace / "learned_skills"
        self.memory_dir = workspace / "conversation_memory"
        self.skills_dir.mkdir(exist_ok=True)
        self.memory_dir.mkdir(exist_ok=True)

        self.skills: Dict[str, LearnedSkill] = {}
        self.memories: List[ConversationMemory] = []
        self.active_observations: Dict[str, Dict] = {}

        # Load existing data
        self._load_skills()
        self._load_memories()

    def _load_skills(self):
        """Load learned skills from disk"""
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skill = LearnedSkill(**skill_data)
                    self.skills[skill.id] = skill
            except Exception as e:
                logger.warning("Failed to load skill {}: {}".format(skill_file, e))

    def _load_memories(self):
        """Load conversation memories"""
        memory_file = self.memory_dir / "memories.json"
        if memory_file.exists():
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                    self.memories = [ConversationMemory(**m) for m in memory_data]
            except Exception as e:
                logger.warning("Failed to load memories: {}".format(e))

    def _save_skill(self, skill: LearnedSkill):
        """Save a skill to disk"""
        skill_file = self.skills_dir / "{}.json".format(skill.id)
        try:
            with open(skill_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(skill), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save skill {}: {}".format(skill.id, e))

    def _save_memories(self):
        """Save memories to disk"""
        memory_file = self.memory_dir / "memories.json"
        try:
            memory_data = [asdict(m) for m in self.memories[-1000:]]  # Keep last 1000
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save memories: {}".format(e))

    def create_skill_from_execution(self, task_type: str, steps: List[str],
                                  success: bool, context: Dict = None) -> Optional[LearnedSkill]:
        """Create a new skill from a task execution"""
        if len(steps) < 2 or not success:
            return None

        # Generate skill name from task type
        skill_name = self._generate_skill_name(task_type, steps)

        # Check if similar skill exists
        existing_skill = self.find_similar_skill(skill_name)
        if existing_skill:
            # Improve existing skill
            execution_data = {
                "task_type": task_type,
                "steps_count": len(steps),
                "context": context or {},
                "timestamp": datetime.now().isoformat()
            }
            existing_skill.record_success(execution_data)
            self._save_skill(existing_skill)
            return existing_skill

        # Create new skill
        skill_id = hashlib.md5(skill_name.encode()).hexdigest()[:8]

        skill = LearnedSkill(
            id=skill_id,
            name=skill_name,
            description="Autonomously learned skill from task execution",
            category=self._categorize_task(task_type),
            steps=steps,
            confidence=0.6  # Initial confidence for new skills
        )

        # Record the successful execution
        execution_data = {
            "task_type": task_type,
            "steps_count": len(steps),
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        skill.record_success(execution_data)

        self.skills[skill.id] = skill
        self._save_skill(skill)

        print("ðŸ§  Learned new skill: {}".format(skill.name))
        return skill

    def _generate_skill_name(self, task_type: str, steps: List[str]) -> str:
        """Generate a descriptive skill name"""
        # Analyze task type and steps
        if "scan" in task_type.lower() or any("scan" in step.lower() for step in steps):
            return "Network Scanning and Analysis"
        elif "web" in task_type.lower() or any("browser" in step.lower() for step in steps):
            return "Web Interaction and Automation"
        elif "file" in task_type.lower() or any("file" in step.lower() for step in steps):
            return "File Operations and Management"
        elif "kali" in task_type.lower() or any("kali" in step.lower() for step in steps):
            return "Kali Linux Tool Execution"
        else:
            # Use first step as basis
            first_step = steps[0] if steps else task_type
            return "{} Workflow".format(first_step.title())

    def _categorize_task(self, task_type: str) -> str:
        """Categorize a task by type"""
        categories = {
            "security": ["scan", "pentest", "kali", "nmap", "nikto"],
            "web": ["browser", "web", "navigate", "click"],
            "file": ["file", "read", "write", "organize"],
            "system": ["system", "process", "monitor"],
            "automation": ["task", "workflow", "script"]
        }

        task_lower = task_type.lower()
        for category, keywords in categories.items():
            if any(keyword in task_lower for keyword in keywords):
                return category

        return "general"

    def find_similar_skill(self, skill_name: str) -> Optional[LearnedSkill]:
        """Find a similar existing skill"""
        skill_name_lower = skill_name.lower()

        for skill in self.skills.values():
            if skill.name.lower() == skill_name_lower:
                return skill

            # Simple similarity check
            skill_words = set(skill.name.lower().split())
            name_words = set(skill_name_lower.split())
            if len(skill_words.intersection(name_words)) / len(skill_words.union(name_words)) > 0.6:
                return skill

        return None

    def store_conversation_memory(self, user_input: str, kai_response: str,
                                context: str = "", tags: List[str] = None,
                                session_id: str = "default"):
        """Store a conversation memory for learning"""
        memory = ConversationMemory(
            id=hashlib.md5("{}{}{}".format(user_input, kai_response, datetime.now().isoformat()).encode()).hexdigest()[:8],
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            kai_response=kai_response,
            context=context,
            tags=tags or [],
            session_id=session_id,
            importance=self._calculate_importance(user_input, kai_response)
        )

        self.memories.append(memory)
        self._save_memories()

        # Extract insights for learning
        insights = self._extract_insights(user_input, kai_response)
        if insights:
            memory.insights.extend(insights)

    def _calculate_importance(self, user_input: str, response: str) -> float:
        """Calculate memory importance score"""
        importance = 1.0

        # Increase for learning moments
        learning_words = ["learn", "remember", "skill", "new", "first time"]
        if any(word in response.lower() for word in learning_words):
            importance += 0.5

        # Increase for problem-solving
        problem_words = ["fix", "solve", "help", "issue", "problem", "error", "debug"]
        if any(word in user_input.lower() for word in problem_words):
            importance += 0.3

        # Increase for tool usage
        if "tool" in response.lower() or "/" in user_input:
            importance += 0.2

        return min(5.0, importance)  # Cap at 5.0

    def _extract_insights(self, user_input: str, response: str) -> List[str]:
        """Extract learning insights from conversation"""
        insights = []

        response_lower = response.lower()

        if "learned" in response_lower or "remember" in response_lower:
            insights.append("User interaction revealed learning opportunity")

        if "tool" in response_lower and ("useful" in response_lower or "effective" in response_lower):
            insights.append("Identified useful tool for user needs")

        if any(word in response_lower for word in ["error", "failed", "issue"]):
            insights.append("Encountered execution challenge - potential improvement area")

        return insights

    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """Search conversation memories"""
        query_lower = query.lower()
        matching_memories = []

        for memory in self.memories:
            if (query_lower in memory.user_input.lower() or
                query_lower in memory.kai_response.lower() or
                any(query_lower in tag for tag in memory.tags)):
                matching_memories.append({
                    "id": memory.id,
                    "timestamp": memory.timestamp,
                    "user_input": memory.user_input,
                    "kai_response": memory.kai_response[:200] + "..." if len(memory.kai_response) > 200 else memory.kai_response,
                    "tags": memory.tags,
                    "importance": memory.importance
                })

        # Sort by importance and recency
        matching_memories.sort(key=lambda x: (x["importance"], x["timestamp"]), reverse=True)
        return matching_memories[:limit]

    def get_skill(self, skill_id: str) -> Optional[LearnedSkill]:
        """Get a skill by ID"""
        return self.skills.get(skill_id)

    def list_skills(self, category: str = None) -> List[LearnedSkill]:
        """List all skills, optionally filtered by category"""
        skills = list(self.skills.values())

        if category:
            skills = [s for s in skills if s.category == category]

        # Sort by confidence and usage
        skills.sort(key=lambda s: (s.confidence, s.usage_count), reverse=True)
        return skills

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_learning_stats for API consistency."""
        return self.get_learning_stats()

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics"""
        total_skills = len(self.skills)
        total_memories = len(self.memories)

        if total_skills > 0:
            avg_confidence = sum(s.confidence for s in self.skills.values()) / total_skills
            avg_success_rate = sum(s.success_rate for s in self.skills.values()) / total_skills
            total_usage = sum(s.usage_count for s in self.skills.values())
        else:
            avg_confidence = avg_success_rate = total_usage = 0

        # Category breakdown
        categories = {}
        for skill in self.skills.values():
            categories[skill.category] = categories.get(skill.category, 0) + 1

        # Recent learning activity
        recent_memories = self.memories[-10:] if self.memories else []
        recent_insights = []
        for memory in recent_memories:
            recent_insights.extend(memory.insights)

        return {
            "total_skills": total_skills,
            "total_memories": total_memories,
            "average_confidence": round(avg_confidence, 2),
            "average_success_rate": round(avg_success_rate, 2),
            "total_skill_usage": total_usage,
            "categories": categories,
            "recent_insights": list(set(recent_insights))[:5],  # Unique recent insights
            "learning_active": True
        }

    def improve_skills_autonomously(self):
        """Autonomously improve existing skills based on accumulated data"""
        for skill in self.skills.values():
            if skill.usage_count >= 3:  # Only improve well-used skills
                improvements = self._analyze_skill_improvements(skill)
                if improvements:
                    for improvement in improvements:
                        skill.add_improvement(improvement)
                    self._save_skill(skill)
                    print("ðŸ§  Improved skill: {}".format(skill.name))

    def _analyze_skill_improvements(self, skill: LearnedSkill) -> List[str]:
        """Analyze a skill and suggest improvements"""
        improvements = []

        # Check success rate
        if skill.success_rate < 0.8 and skill.usage_count >= 5:
            improvements.append("Improve reliability - success rate below 80%")

        # Check for common failure patterns
        failed_count = len(skill.failed_executions)
        if failed_count > 0:
            improvements.append("Address {} failed executions".format(failed_count))

        # Suggest optimizations based on usage
        if skill.usage_count >= 10 and skill.confidence < 0.7:
            improvements.append("Increase confidence through more successful executions")

        return improvements

    def get_memory_insights(self, days_back: int = 7) -> Dict[str, Any]:
        """Get insights from conversation memories"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_memories = [
            m for m in self.memories
            if datetime.fromisoformat(m.timestamp) > cutoff_date
        ]

        # Analyze patterns
        total_interactions = len(recent_memories)
        avg_importance = sum(m.importance for m in recent_memories) / total_interactions if total_interactions > 0 else 0

        # Common tags
        all_tags = []
        for memory in recent_memories:
            all_tags.extend(memory.tags)

        from collections import Counter
        tag_counts = Counter(all_tags)
        top_tags = tag_counts.most_common(5)

        # Learning insights
        all_insights = []
        for memory in recent_memories:
            all_insights.extend(memory.insights)

        insight_counts = Counter(all_insights)
        top_insights = insight_counts.most_common(3)

        return {
            "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
            "top_insights": [{"insight": insight, "frequency": freq} for insight, freq in top_insights]
        }
