from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage
from typing import Optional
from app.db.crud_token import TokenUsageCRUD
from app.db.crud_chat import ChatCRUD
from app.schemas.chat import ChatResponse
from app.ai.graph.agent import agent

class ChatService:
    @staticmethod
    def process_chat(message: str, conversation_id: Optional[int], user_id: int, user_tier: str, db: Session) -> ChatResponse:
        # 1. Policy Enforcement (token check)
        user_limit = TokenUsageCRUD.get_user_limit(db, user_id)
        
        if not user_limit:
            # Initialize tokens for first time interactions
            user_limit = TokenUsageCRUD.create_user_limit(db, user_id, initial_limit=5000)
            
        if user_limit.daily_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Daily token limit exceeded"
            )
            
        # 2. Handle DB Conversation
        if not conversation_id:
            title = message[:30] + "..." if len(message) > 30 else message
            conversation = ChatCRUD.create_conversation(db, user_id, title)
            conversation_id = conversation.id
        else:
            conversation = ChatCRUD.get_conversation(db, conversation_id)
            if not conversation or conversation.user_id != user_id:
                raise HTTPException(status_code=404, detail="Conversation not found")
                
        # Save human message
        ChatCRUD.add_message(db, conversation_id, "user", message)
        
        # Load history
        history = ChatCRUD.get_messages_for_conversation(db, conversation_id)
        formatted_history = []
        for msg in history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            else:
                formatted_history.append(AIMessage(content=msg.content))
                
        # 3. Call LangGraph (Inference Engine)
        input_state = {"messages": formatted_history}
        config = {"configurable": {"user_id": user_id, "user_tier": user_tier}}
        
        try:
            result = agent.invoke(input_state, config=config)
            final_message = result["messages"][-1]
            response_content = final_message.content
            
            # Usage Metering
            tokens_used = 0
            
            if hasattr(final_message, "response_metadata") and final_message.response_metadata:
                token_usage = final_message.response_metadata.get("token_usage", {})
                tokens_used = token_usage.get("total_tokens", 0)
            
            if tokens_used <= 0 and hasattr(final_message, "usage_metadata") and final_message.usage_metadata:
                tokens_used = final_message.usage_metadata.get("total_tokens", 0)
                
            if tokens_used <= 0:
                tokens_used = len(message.split()) + len(response_content.split())
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating AI response: {str(e)}"
            )
            
        # 4. Save AI message
        ChatCRUD.add_message(db, conversation_id, "assistant", response_content)
            
        # 5. Update usage (Billing/Update)
        updated_limit = TokenUsageCRUD.deduct_tokens(db, user_id, tokens_used)
        
        # 6. Return response
        return ChatResponse(
            response=response_content,
            tokens_used=tokens_used,
            tokens_remaining=updated_limit.daily_limit,
            conversation_id=conversation_id
        )
