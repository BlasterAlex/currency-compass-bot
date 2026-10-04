from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class UserCurrency(Base):
    __tablename__ = "user_currencies"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
