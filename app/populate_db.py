
"""
Асинхронный скрипт для заполнения базы данных тестовыми данными
"""

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.models import Building, Activity, Organization, OrganizationPhone


async def create_test_data():
    """Создает тестовые данные в базе данных"""
    

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        try:

            print("Очистка существующих данных...")
            
            await db.execute(delete(OrganizationPhone))
            await db.execute(delete(Organization))
            await db.execute(delete(Activity))
            await db.execute(delete(Building))
            await db.commit()
            

            print("Создание зданий...")
            
            buildings_data = [
                {
                    "address": "г. Москва, ул. Тверская, д. 1",
                    "latitude": 55.759020,
                    "longitude": 37.614558
                },
                {
                    "address": "г. Москва, ул. Арбат, д. 15",
                    "latitude": 55.752023,
                    "longitude": 37.592159
                },
                {
                    "address": "г. Москва, Красная площадь, д. 1",
                    "latitude": 55.753544,
                    "longitude": 37.621202
                },
                {
                    "address": "г. Санкт-Петербург, Невский проспект, д. 20",
                    "latitude": 59.934280,
                    "longitude": 30.335099
                },
                {
                    "address": "г. Санкт-Петербург, ул. Рубинштейна, д. 5",
                    "latitude": 59.928322,
                    "longitude": 30.335930
                },
                {
                    "address": "г. Екатеринбург, ул. Вайнера, д. 10",
                    "latitude": 56.838607,
                    "longitude": 60.603817
                },
                {
                    "address": "г. Новосибирск, Красный проспект, д. 25",
                    "latitude": 55.030204,
                    "longitude": 82.920430
                }
            ]
            
            buildings = []
            for building_data in buildings_data:
                building = Building(**building_data)
                db.add(building)
                buildings.append(building)
            
            await db.commit()
            

            for building in buildings:
                await db.refresh(building)
            
            print(f"Создано {len(buildings)} зданий")
            

            print("Создание видов деятельности...")
            

            activities_level_1 = [
                {"name": "Еда", "level": 1, "parent_id": None},
                {"name": "Автомобили", "level": 1, "parent_id": None},
                {"name": "Образование", "level": 1, "parent_id": None},
                {"name": "Медицина", "level": 1, "parent_id": None},
                {"name": "Услуги", "level": 1, "parent_id": None}
            ]
            
            level_1_activities = []
            for activity_data in activities_level_1:
                activity = Activity(**activity_data)
                db.add(activity)
                level_1_activities.append(activity)
            
            await db.commit()
            

            for activity in level_1_activities:
                await db.refresh(activity)
            

            activities_level_2_data = [

                {"name": "Мясная продукция", "level": 2, "parent_name": "Еда"},
                {"name": "Молочная продукция", "level": 2, "parent_name": "Еда"},
                {"name": "Хлебобулочные изделия", "level": 2, "parent_name": "Еда"},
                {"name": "Кондитерские изделия", "level": 2, "parent_name": "Еда"},
                

                {"name": "Грузовые", "level": 2, "parent_name": "Автомобили"},
                {"name": "Легковые", "level": 2, "parent_name": "Автомобили"},
                {"name": "Мотоциклы", "level": 2, "parent_name": "Автомобили"},
                

                {"name": "Школьное образование", "level": 2, "parent_name": "Образование"},
                {"name": "Высшее образование", "level": 2, "parent_name": "Образование"},
                {"name": "Курсы и тренинги", "level": 2, "parent_name": "Образование"},
                

                {"name": "Стоматология", "level": 2, "parent_name": "Медицина"},
                {"name": "Терапия", "level": 2, "parent_name": "Медицина"},
                {"name": "Хирургия", "level": 2, "parent_name": "Медицина"},
                

                {"name": "Клининг", "level": 2, "parent_name": "Услуги"},
                {"name": "Ремонт", "level": 2, "parent_name": "Услуги"},
                {"name": "Консультации", "level": 2, "parent_name": "Услуги"}
            ]
            
            level_2_activities = []
            for activity_data in activities_level_2_data:
                parent_name = activity_data.pop("parent_name")
                parent = next((a for a in level_1_activities if a.name == parent_name), None)
                if parent:
                    activity_data["parent_id"] = parent.id
                    activity = Activity(**activity_data)
                    db.add(activity)
                    level_2_activities.append(activity)
            
            await db.commit()
            

            for activity in level_2_activities:
                await db.refresh(activity)
            

            activities_level_3_data = [

                {"name": "Запчасти", "level": 3, "parent_name": "Легковые"},
                {"name": "Аксессуары", "level": 3, "parent_name": "Легковые"},
                {"name": "Шины", "level": 3, "parent_name": "Легковые"},
                

                {"name": "Сантехника", "level": 3, "parent_name": "Ремонт"},
                {"name": "Электрика", "level": 3, "parent_name": "Ремонт"},
                {"name": "Отделочные работы", "level": 3, "parent_name": "Ремонт"},
                

                {"name": "Детская стоматология", "level": 3, "parent_name": "Стоматология"},
                {"name": "Ортодонтия", "level": 3, "parent_name": "Стоматология"},
                {"name": "Имплантация", "level": 3, "parent_name": "Стоматология"}
            ]
            
            level_3_activities = []
            for activity_data in activities_level_3_data:
                parent_name = activity_data.pop("parent_name")
                parent = next((a for a in level_2_activities if a.name == parent_name), None)
                if parent:
                    activity_data["parent_id"] = parent.id
                    activity = Activity(**activity_data)
                    db.add(activity)
                    level_3_activities.append(activity)
            
            await db.commit()
            

            result = await db.execute(select(Activity))
            all_activities = result.scalars().all()
            print(f"Создано {len(all_activities)} видов деятельности")
            

            print("Создание организаций...")
            
            organizations_data = [
                {
                    "name": 'ООО "Рога и Копыта"',
                    "building_id": buildings[0].id,
                    "phones": ["8-495-123-45-67", "8-495-765-43-21"],
                    "activity_names": ["Мясная продукция", "Молочная продукция"]
                },
                {
                    "name": 'ИП "Иванов И.И."',
                    "building_id": buildings[1].id,
                    "phones": ["8-916-555-12-34"],
                    "activity_names": ["Хлебобулочные изделия"]
                },
                {
                    "name": 'ООО "АвтоЗапчасти+"',
                    "building_id": buildings[2].id,
                    "phones": ["8-495-777-88-99", "8-495-111-22-33", "8-800-555-35-35"],
                    "activity_names": ["Запчасти", "Аксессуары"]
                },
                {
                    "name": 'Стоматологическая клиника "Белые зубки"',
                    "building_id": buildings[3].id,
                    "phones": ["8-812-999-88-77"],
                    "activity_names": ["Стоматология", "Детская стоматология", "Ортодонтия"]
                },
                {
                    "name": 'Автосалон "Премиум Авто"',
                    "building_id": buildings[4].id,
                    "phones": ["8-812-333-44-55", "8-812-666-77-88"],
                    "activity_names": ["Легковые"]
                },
                {
                    "name": 'Учебный центр "Знание"',
                    "building_id": buildings[5].id,
                    "phones": ["8-343-123-45-67"],
                    "activity_names": ["Курсы и тренинги", "Консультации"]
                },
                {
                    "name": 'Клининговая компания "Чистота"',
                    "building_id": buildings[6].id,
                    "phones": ["8-383-999-11-22"],
                    "activity_names": ["Клининг"]
                },
                {
                    "name": 'ООО "СтройМастер"',
                    "building_id": buildings[0].id,
                    "phones": ["8-495-444-55-66", "8-495-777-88-99"],
                    "activity_names": ["Ремонт", "Сантехника", "Электрика", "Отделочные работы"]
                },
                {
                    "name": 'Медицинский центр "Здоровье"',
                    "building_id": buildings[1].id,
                    "phones": ["8-916-222-33-44"],
                    "activity_names": ["Терапия", "Хирургия"]
                },
                {
                    "name": 'Кондитерская "Сладкий рай"',
                    "building_id": buildings[2].id,
                    "phones": ["8-495-888-99-00"],
                    "activity_names": ["Кондитерские изделия"]
                }
            ]
            

            organizations = []
            for org_data in organizations_data:
                organization = Organization(
                    name=org_data["name"],
                    building_id=org_data["building_id"]
                )
                db.add(organization)
                organizations.append((organization, org_data))
            
            await db.flush()
            

            for organization, org_data in organizations:

                for phone_number in org_data["phones"]:
                    phone = OrganizationPhone(
                        organization_id=organization.id,
                        phone_number=phone_number
                    )
                    db.add(phone)
                


                activity_ids = []
                for activity_name in org_data["activity_names"]:
                    activity = next((a for a in all_activities if a.name == activity_name), None)
                    if activity:
                        activity_ids.append(activity.id)
                

                org_with_activities = await db.execute(
                    select(Organization)
                    .options(selectinload(Organization.activities))
                    .where(Organization.id == organization.id)
                )
                org_instance = org_with_activities.scalar_one()
                

                for activity_id in activity_ids:
                    activity = next((a for a in all_activities if a.id == activity_id), None)
                    if activity:
                        org_instance.activities.append(activity)
            
            await db.commit()
            

            organizations_result = await db.execute(select(Organization))
            organizations_count = len(organizations_result.scalars().all())
            
            phones_result = await db.execute(select(OrganizationPhone))
            phones_count = len(phones_result.scalars().all())
            
            print(f"Создано {organizations_count} организаций")
            print(f"Создано {phones_count} телефонных номеров")
            
            print("\n=== ТЕСТОВЫЕ ДАННЫЕ УСПЕШНО СОЗДАНЫ ===")
            print("\nСтатистика:")
            print(f"- Зданий: {len(buildings)}")
            print(f"- Видов деятельности: {len(all_activities)}")
            print(f"- Организаций: {organizations_count}")
            print(f"- Телефонов: {phones_count}")
            
        except Exception as e:
            print(f"Ошибка при создании тестовых данных: {e}")
            await db.rollback()
            raise


async def main():
    """Главная функция для запуска скрипта"""
    print("Запуск асинхронного скрипта создания тестовых данных...")
    await create_test_data()
    print("Скрипт завершен успешно!")


if __name__ == "__main__":

    asyncio.run(main())