from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.schemas.skill import SkillListResponse
from server.models.enums import ProficiencyLevel, SkillCategory


class ManageSkillsScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("MANAGE SKILLS")
        print()

        employee_id_str = self._reader.read_line("Enter Employee ID: ")
        if not employee_id_str.isdigit():
            self._renderer.render_error("Employee ID must be a number.")
            return ScreenResult.RETRY

        employee_id = int(employee_id_str)
        try:
            employee = await self._client.get_employee(employee_id)
            skills = await self._client.list_employee_skills(employee_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        while True:
            print()
            print(f"── {employee.full_name} ─────────────────────────────────")
            print("Current Skills:")
            if not skills.items:
                print("  (none)")
            else:
                for index, skill in enumerate(skills.items, start=1):
                    print(
                        f"  {index}.  {skill.skill_name:<18}"
                        f"{skill.proficiency_level}"
                    )
            print("─" * 46)
            print("1. Add Skill")
            print("2. Update Proficiency Level")
            print("3. Remove Skill")
            print("4. Back")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            if option == "4":
                return ScreenResult.BACK
            if option == "1":
                skills = await self._add_skill(employee_id, skills)
                continue
            if option == "2":
                skills = await self._update_proficiency(employee_id, skills)
                continue
            if option == "3":
                skills = await self._remove_skill(employee_id, skills)
                continue
            self._renderer.render_error("Invalid option. Please enter 1–4.")

    async def _add_skill(
        self, employee_id: int, skills: SkillListResponse
    ) -> SkillListResponse:
        skill_name = self._reader.read_line("Skill Name        : ")
        print("Category          : (1) Backend  (2) Frontend  (3) DevOps  (4) QA  (5) Other")
        category_choice = self._reader.read_line("Enter choice      : ")
        print("Proficiency Level : (1) Beginner  (2) Intermediate  (3) Advanced")
        proficiency_choice = self._reader.read_line("Enter choice      : ")

        category = self._parse_category(category_choice)
        proficiency = self._parse_proficiency(proficiency_choice)
        if category is None or proficiency is None:
            self._renderer.render_error("Invalid category or proficiency choice.")
            return skills
        if not skill_name:
            self._renderer.render_error("Skill name is required.")
            return skills

        try:
            await self._client.add_skill(
                employee_id=employee_id,
                skill_name=skill_name,
                category=category.value,
                proficiency_level=proficiency.value,
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return skills
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return skills

        self._renderer.render_message("Skill added. ✓")
        return await self._client.list_employee_skills(employee_id)

    async def _update_proficiency(
        self, employee_id: int, skills: SkillListResponse
    ) -> SkillListResponse:
        if not skills.items:
            self._renderer.render_error("No skills to update.")
            return skills

        index_str = self._reader.read_line("Skill number to update: ")
        if not index_str.isdigit():
            self._renderer.render_error("Enter a valid skill number.")
            return skills

        index = int(index_str) - 1
        if index < 0 or index >= len(skills.items):
            self._renderer.render_error("Invalid skill number.")
            return skills

        print("Proficiency Level : (1) Beginner  (2) Intermediate  (3) Advanced")
        proficiency_choice = self._reader.read_line("Enter choice      : ")
        proficiency = self._parse_proficiency(proficiency_choice)
        if proficiency is None:
            self._renderer.render_error("Invalid proficiency choice.")
            return skills

        skill = skills.items[index]
        try:
            await self._client.update_skill_proficiency(
                skill.id, proficiency.value
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return skills
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return skills

        self._renderer.render_message("Proficiency updated. ✓")
        return await self._client.list_employee_skills(employee_id)

    async def _remove_skill(
        self, employee_id: int, skills: SkillListResponse
    ) -> SkillListResponse:
        if not skills.items:
            self._renderer.render_error("No skills to remove.")
            return skills

        index_str = self._reader.read_line("Skill number to remove: ")
        if not index_str.isdigit():
            self._renderer.render_error("Enter a valid skill number.")
            return skills

        index = int(index_str) - 1
        if index < 0 or index >= len(skills.items):
            self._renderer.render_error("Invalid skill number.")
            return skills

        skill = skills.items[index]
        try:
            await self._client.remove_skill(skill.id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return skills
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return skills

        self._renderer.render_message("Skill removed. ✓")
        return await self._client.list_employee_skills(employee_id)

    def _parse_category(self, choice: str) -> SkillCategory | None:
        match choice.strip():
            case "1":
                return SkillCategory.BACKEND
            case "2":
                return SkillCategory.FRONTEND
            case "3":
                return SkillCategory.DEVOPS
            case "4":
                return SkillCategory.QA
            case "5":
                return SkillCategory.OTHER
            case _:
                return None

    def _parse_proficiency(self, choice: str) -> ProficiencyLevel | None:
        match choice.strip():
            case "1":
                return ProficiencyLevel.BEGINNER
            case "2":
                return ProficiencyLevel.INTERMEDIATE
            case "3":
                return ProficiencyLevel.ADVANCED
            case _:
                return None
