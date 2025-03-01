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
    
    def run_task_for_target(
        self,
        target_type: str,
        target_id: str,
        task: str,
        context: Optional[str] = None,
        prompt_template: Optional[str] = None,
        override: bool = False,
        max_words: Optional[int] = None,
        max_tokens: Optional[int] = None
    ):
        """Run a content processing task on any target type (message, conversation, chunk).
        
        Args:
            target_type: Type of target ('message', 'conversation', 'chunk')
            target_id: ID of the target to process
            task: Task type to run (e.g., "summary", "gencom")
            context: Optional context for the task
            prompt_template: Optional custom prompt template
            override: Whether to override existing output
            max_words: Optional maximum word count for the output
            max_tokens: Optional maximum token count for the output
            
        Returns:
            The AgentOutput object with the processing result
        """
        with get_session() as session:
            # Get the content based on target type
            if target_type == "message":
                from carchive.database.models import Message
                target = session.query(Message).filter_by(id=target_id).first()
                if not target:
                    raise ValueError(f"Message {target_id} not found.")
                content_text = target.content
            
            elif target_type == "conversation":
                from carchive.database.models import Conversation, Message
                target = session.query(Conversation).filter_by(id=target_id).first()
                if not target:
                    raise ValueError(f"Conversation {target_id} not found.")
                # Get all messages in conversation
                messages = session.query(Message).filter_by(conversation_id=target.id).order_by(Message.created_at).all()
                # Format conversation content as a transcript
                content_text = self._format_conversation_transcript(messages)
                
            elif target_type == "chunk":
                from carchive.database.models import Chunk
                target = session.query(Chunk).filter_by(id=target_id).first()
                if not target:
                    raise ValueError(f"Chunk {target_id} not found.")
                content_text = target.content
                
            else:
                raise ValueError(f"Unsupported target type: {target_type}")

            # Check for existing output
            existing = session.query(AgentOutput).filter(
                AgentOutput.target_type == target_type,
                AgentOutput.target_id == target_id,
                AgentOutput.output_type == task
            ).first()

            if existing and not override:
                return existing
            
            # Convert string context to dict format if provided
            context_dict = None
            if context:
                context_dict = {"system_prompt": context}

            # If max_words or max_tokens is specified, update the prompt template
            effective_prompt = prompt_template
            
            if max_words:
                if effective_prompt:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
                else:
                    effective_prompt = f"Please limit your response to approximately {max_words} words.\n\n{{content}}"
                    
            if max_tokens:
                if effective_prompt:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
                else:
                    effective_prompt = f"Please limit your response to approximately {max_tokens} tokens.\n\n{{content}}"
            
            output_text = self.agent.process_task(
                task=task, 
                content=content_text, 
                context=context_dict, 
                prompt_template=effective_prompt
            )

            if existing and override:
                existing.content = output_text
                session.commit()
                session.refresh(existing)
                return existing

            agent_output = AgentOutput(
                target_type=target_type,
                target_id=target_id,
                output_type=task,
                content=output_text,
                agent_name=self.agent.agent_name
            )
            session.add(agent_output)
            session.commit()
            session.refresh(agent_output)
            return agent_output
    
    def run_task_for_message(
        self,
        message_id: str,
        task: str,
        context: Optional[str] = None,
        prompt_template: Optional[str] = None,
        override: bool = False
    ):
        """Backwards-compatible method that calls run_task_for_target with message target type.
        
        Args:
            message_id: ID of the message to process
            task: Task type to run (e.g., "summary", "gencom")
            context: Optional context for the task
            prompt_template: Optional custom prompt template
            override: Whether to override existing output
            
        Returns:
            The AgentOutput object with the processing result
        """
        return self.run_task_for_target(
            target_type="message",
            target_id=message_id,
            task=task,
            context=context,
            prompt_template=prompt_template,
            override=override
        )
    
    def _format_conversation_transcript(self, messages):
        """Format conversation messages as a transcript for processing.
        
        Args:
            messages: List of Message objects in the conversation
            
        Returns:
            Formatted conversation transcript as string
        """
        transcript = []
        for msg in messages:
            role = msg.role.upper()
            content = msg.content if msg.content else ""
            transcript.append(f"{role}: {content}")
        
        return "\n\n".join(transcript)