# carchive/src/carchive/pipelines/content_tasks.py
from typing import Optional
from carchive.database.session import get_session
from carchive.database.models import Message, AgentOutput
from carchive.agents import get_agent

class ContentTaskManager:
    def __init__(self, provider: str = "ollama"):
        """Initialize the content task manager.
        
        Args:
            provider: Provider to use for content processing (default: "ollama")
        """
        # Get a content agent from our new agent system
        self.agent = get_agent("content", provider)
    
    def run_task_for_message(
        self,
        message_id: str,
        task: str,
        context: Optional[str] = None,
        prompt_template: Optional[str] = None,
        override: bool = False
    ):
        """Run a content processing task on a specific message.
        
        Args:
            message_id: ID of the message to process
            task: Task type to run (e.g., "summary", "gencom")
            context: Optional context for the task
            prompt_template: Optional custom prompt template
            override: Whether to override existing output
            
        Returns:
            The AgentOutput object with the processing result
        """
        with get_session() as session:
            msg = session.query(Message).filter_by(id=message_id).first()
            if not msg:
                raise ValueError(f"Message {message_id} not found.")

            existing = session.query(AgentOutput).filter(
                AgentOutput.target_type == "message",
                AgentOutput.target_id == msg.id,
                AgentOutput.output_type == task
            ).first()

            if existing and not override:
                return existing
            
            # Convert string context to dict format if provided
            context_dict = None
            if context:
                context_dict = {"system_prompt": context}

            output_text = self.agent.process_task(
                task=task, 
                content=msg.content, 
                context=context_dict, 
                prompt_template=prompt_template
            )

            if existing and override:
                existing.content = output_text
                session.commit()
                session.refresh(existing)
                return existing

            agent_output = AgentOutput(
                target_type="message",
                target_id=msg.id,
                output_type=task,
                content=output_text,
                agent_name=self.agent.agent_name
            )
            session.add(agent_output)
            session.commit()
            session.refresh(agent_output)
            return agent_output