import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.features.users.models import User
from app.features.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self,
        firebase_uid: str,
        email: str,
        data: UserCreate,
    ) -> User:
        # Check if user already exists
        existing = await self.get_user_by_firebase_uid(firebase_uid)
        if existing:
            raise ConflictException("User profile already exists")

        user = User(
            firebase_uid=firebase_uid,
            email=email,
            full_name=data.full_name,
            phone_number=data.phone_number,
            date_of_birth=data.date_of_birth,
            gender=data.gender.value if data.gender else None,
            profile_image_url=data.profile_image_url,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # method to find user by Firebase UID
    async def get_user_by_firebase_uid(self, uid: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.firebase_uid == uid)
        )
        return result.scalar_one_or_none()

    # method to find user by ID
    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException("User not found")
        return user

    # method to update user profile
    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get_user_by_id(user_id)

        update_data = data.model_dump(exclude_unset=True)
   
        if "gender" in update_data and update_data["gender"] is not None:
            update_data["gender"] = update_data["gender"].value

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        await self.db.refresh(user)
        return user

    # method to list users with pagination
    async def list_users(
        self, page: int = 1, limit: int = 20
    ) -> tuple[list[User], int]:
     
        limit = min(limit, 100)
        offset = (page - 1) * limit

        # Total count
        count_result = await self.db.execute(select(func.count(User.id)))
        total = count_result.scalar_one()

        # Paginated results
        result = await self.db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        users = list(result.scalars().all())

        return users, total
