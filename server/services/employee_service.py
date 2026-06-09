from dataclasses import dataclass
from datetime import date

from server.core.exceptions import (
    EmployeeAlreadyInactiveError,
    EmployeeNotFoundError,
    InvalidManagerRoleError,
    InvalidUserRoleForEmployeeError,
    ManagerProfileNotFoundError,
    ManagerUserNotFoundError,
    SelfManagerAssignmentError,
    UserNotFoundError,
)
from server.models.employee import Employee
from server.models.enums import EmployeeStatus, UserRole, UserStatus
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.employee_repository import EmployeeRepository
from server.repositories.user_repository import UserRepository
from server.schemas.requests.employee import AssignManagerRequest, UpdateEmployeeRequest


@dataclass(frozen=True)
class EmployeeListResult:
    items: list[Employee]
    total: int
    bench_count: int
    allocated_count: int


@dataclass(frozen=True)
class EmployeeUpsertResult:
    employee: Employee
    created: bool


class EmployeeService:
    def __init__(
        self,
        employee_repository: EmployeeRepository,
        user_repository: UserRepository,
        allocation_repository: AllocationRepository,
    ) -> None:
        self._employee_repository = employee_repository
        self._user_repository = user_repository
        self._allocation_repository = allocation_repository

    async def update_employee(
        self, user_id: int, dto: UpdateEmployeeRequest
    ) -> EmployeeUpsertResult:
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found")
        if user.role not in (UserRole.EMPLOYEE, UserRole.MANAGER):
            raise InvalidUserRoleForEmployeeError(
                "User must have EMPLOYEE or MANAGER role"
            )

        existing = await self._employee_repository.find_by_user_id(user_id)
        if existing is None:
            employee = Employee(
                user_id=user_id,
                full_name=dto.full_name,
                email=str(dto.email),
                department=dto.department,
                designation=dto.designation,
                status=EmployeeStatus.BENCH,
                is_active=True,
            )
            saved = await self._employee_repository.save(employee)
            return EmployeeUpsertResult(employee=saved, created=True)

        existing.full_name = dto.full_name
        existing.email = str(dto.email)
        existing.department = dto.department
        existing.designation = dto.designation
        saved = await self._employee_repository.save(existing)
        return EmployeeUpsertResult(employee=saved, created=False)

    async def list_employees(
        self,
        *,
        status: EmployeeStatus | None,
        department: str | None,
        limit: int,
        offset: int,
    ) -> EmployeeListResult:
        items = await self._employee_repository.list_employees(
            status=status, department=department, limit=limit, offset=offset
        )
        total = await self._employee_repository.count_active_employees(
            status=status, department=department
        )
        bench_count = await self._employee_repository.count_by_status(
            EmployeeStatus.BENCH
        )
        allocated_count = await self._employee_repository.count_by_status(
            EmployeeStatus.ALLOCATED
        )
        return EmployeeListResult(
            items=items,
            total=total,
            bench_count=bench_count,
            allocated_count=allocated_count,
        )

    async def get_employee(self, employee_id: int) -> Employee:
        employee = await self._employee_repository.get_by_id(employee_id)
        if employee is None:
            raise EmployeeNotFoundError("Employee not found")
        return employee

    async def get_active_allocations(self, employee_id: int):
        await self.get_employee(employee_id)
        return await self._allocation_repository.find_active_by_employee(employee_id)

    async def assign_manager(self, dto: AssignManagerRequest) -> Employee:
        if dto.employee_user_id == dto.manager_user_id:
            raise SelfManagerAssignmentError(
                "Employee and manager cannot be the same user"
            )

        employee = await self._employee_repository.find_by_user_id(
            dto.employee_user_id
        )
        if employee is None:
            raise EmployeeNotFoundError("Employee profile not found for user")

        manager_user = await self._user_repository.find_by_id(dto.manager_user_id)
        if manager_user is None:
            raise ManagerUserNotFoundError("Manager user not found")
        if manager_user.role != UserRole.MANAGER:
            raise InvalidManagerRoleError("Manager user must have MANAGER role")

        manager_employee = await self._employee_repository.find_by_user_id(
            dto.manager_user_id
        )
        if manager_employee is None:
            raise ManagerProfileNotFoundError(
                "Manager user does not have an employee profile"
            )

        if employee.id == manager_employee.id:
            raise SelfManagerAssignmentError("Employee cannot be their own manager")

        employee.manager_id = manager_employee.id
        return await self._employee_repository.save(employee)

    async def deactivate_employee(self, employee_id: int) -> Employee:
        employee = await self.get_employee(employee_id)
        if not employee.is_active:
            raise EmployeeAlreadyInactiveError("Employee is already inactive")

        today = date.today()
        active_allocations = (
            await self._allocation_repository.find_active_by_employee(employee_id)
        )
        for allocation in active_allocations:
            allocation.to_date = today
            await self._allocation_repository.save(allocation)

        employee.is_active = False
        employee.status = EmployeeStatus.BENCH
        await self._employee_repository.save(employee)

        user = await self._user_repository.find_by_id(employee.user_id)
        if user is not None:
            user.status = UserStatus.INACTIVE
            await self._user_repository.save(user)

        return employee
