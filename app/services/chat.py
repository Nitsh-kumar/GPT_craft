from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage
from app.db.crud_token import TokenUsageCRUD
from app.schemas.chat import ChatResponse
from app.ai.graph.agent import agent

class ChatService:
    @staticmethod
    def process_chat(message: str, user_id: int, db: Session) -> ChatResponse:
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
            
        # 2. Call LangGraph (Inference Engine)
        input_state = {"messages": [HumanMessage(content=message)]}
        config = {"configurable": {"user_id": user_id}}
        
        try:
            result = agent.invoke(input_state, config=config)
            final_message = result["messages"][-1]
            response_content = final_message.content
            
            # 3. Usage Metering
            # Extract token usage metadata from the response 
            tokens_used = 0
            
            # Attempt 1: response_metadata (common for ChatGroq wrapper)
            if hasattr(final_message, "response_metadata") and final_message.response_metadata:
                token_usage = final_message.response_metadata.get("token_usage", {})
                tokens_used = token_usage.get("total_tokens", 0)
            
            # Attempt 2: usage_metadata (standard langchain models)
            if tokens_used <= 0 and hasattr(final_message, "usage_metadata") and final_message.usage_metadata:
                tokens_used = final_message.usage_metadata.get("total_tokens", 0)
                
            # Fallback heuristic if metrics not available
            if tokens_used <= 0:
                tokens_used = len(message.split()) + len(response_content.split())
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating AI response: {str(e)}"
            )
            
        # 4. Update usage (Billing/Update)
        updated_limit = TokenUsageCRUD.deduct_tokens(db, user_id, tokens_used)
        
        # 5. Return response
        return ChatResponse(
            response=response_content,
            tokens_used=tokens_used,
            tokens_remaining=updated_limit.daily_limit
        )
