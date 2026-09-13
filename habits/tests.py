from datetime import time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from habits.models import Habit
from users.models import User


class HabitBaseTestCase(APITestCase):
    """Владелец, посторонний и пара привычек."""

    def setUp(self):
        self.owner = User.objects.create(email='owner@test.ru')
        self.stranger = User.objects.create(email='stranger@test.ru')

        self.pleasant = Habit.objects.create(
            user=self.owner,
            action='принять ванну с пеной',
            time=time(21, 0),
            place='дома',
            is_pleasant=True,
            duration=120,
        )
        self.useful = Habit.objects.create(
            user=self.owner,
            action='гулять вокруг квартала',
            time=time(19, 30),
            place='район у дома',
            related_habit=self.pleasant,
            duration=120,
        )
        self.client.force_authenticate(user=self.owner)


class HabitValidatorsTestCase(HabitBaseTestCase):
    """Пять правил из задания."""

    def setUp(self):
        super().setUp()
        self.url = reverse('habits:habit-list')
        self.payload = {
            'action': 'делать зарядку',
            'time': '07:00:00',
            'place': 'дома',
            'duration': 60,
        }

    def _post(self, **extra):
        return self.client.post(self.url, {**self.payload, **extra})

    def test_reward_and_related_habit_together_rejected(self):
        response = self._post(reward='съесть десерт', related_habit=self.pleasant.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('одно', str(response.json()))

    def test_reward_alone_is_allowed(self):
        self.assertEqual(self._post(reward='съесть десерт').status_code, status.HTTP_201_CREATED)

    def test_related_habit_alone_is_allowed(self):
        response = self._post(related_habit=self.pleasant.pk)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duration_over_two_minutes_rejected(self):
        response = self._post(duration=121)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('120', str(response.json()))

    def test_duration_exactly_two_minutes_is_allowed(self):
        self.assertEqual(self._post(duration=120).status_code, status.HTTP_201_CREATED)

    def test_useful_habit_cannot_be_related(self):
        """В связанные попадают только приятные привычки."""
        response = self._post(related_habit=self.useful.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('приятная', str(response.json()))

    def test_pleasant_habit_cannot_have_reward(self):
        response = self._post(is_pleasant=True, reward='ещё десерт')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('наград', str(response.json()).lower())

    def test_pleasant_habit_cannot_have_related_habit(self):
        response = self._post(is_pleasant=True, related_habit=self.pleasant.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_periodicity_over_week_rejected(self):
        response = self._post(periodicity=8)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('7', str(response.json()))

    def test_periodicity_of_seven_days_is_allowed(self):
        self.assertEqual(self._post(periodicity=7).status_code, status.HTTP_201_CREATED)

    def test_zero_periodicity_rejected(self):
        self.assertEqual(self._post(periodicity=0).status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_link_someone_elses_habit(self):
        alien = Habit.objects.create(
            user=self.stranger, action='чужая приятная', time=time(8, 0),
            place='где-то', is_pleasant=True,
        )
        response = self._post(related_habit=alien.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('своей', str(response.json()))

    def test_validators_work_on_partial_update(self):
        """PATCH тоже проверяется: поля добираются из объекта в базе."""
        url = reverse('habits:habit-detail', args=(self.useful.pk,))
        response = self.client.patch(url, {'reward': 'десерт'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HabitCrudTestCase(HabitBaseTestCase):
    """CRUD своих привычек."""

    def test_anonymous_has_no_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('habits:habit-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_becomes_author(self):
        response = self.client.post(reverse('habits:habit-list'), {
            'action': 'читать книгу', 'time': '22:00:00', 'place': 'кресло', 'duration': 100,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Habit.objects.get(pk=response.json()['id']).user, self.owner)

    def test_user_sees_only_own_habits(self):
        Habit.objects.create(user=self.stranger, action='чужая', time=time(9, 0), place='офис')

        data = self.client.get(reverse('habits:habit-list')).json()

        self.assertEqual(data['count'], 2)
        actions = [item['action'] for item in data['results']]
        self.assertNotIn('чужая', actions)

    def test_retrieve_own_habit(self):
        url = reverse('habits:habit-detail', args=(self.useful.pk,))
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['action'], 'гулять вокруг квартала')

    def test_someone_elses_habit_is_not_found(self):
        alien = Habit.objects.create(user=self.stranger, action='чужая', time=time(9, 0), place='офис')
        url = reverse('habits:habit-detail', args=(alien.pk,))

        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_update_own_habit(self):
        url = reverse('habits:habit-detail', args=(self.pleasant.pk,))
        response = self.client.patch(url, {'place': 'ванная'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pleasant.refresh_from_db()
        self.assertEqual(self.pleasant.place, 'ванная')

    def test_delete_own_habit(self):
        url = reverse('habits:habit-detail', args=(self.useful.pk,))

        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(pk=self.useful.pk).exists())

    def test_sentence_is_built_from_fields(self):
        url = reverse('habits:habit-detail', args=(self.useful.pk,))
        sentence = self.client.get(url).json()['sentence']

        self.assertEqual(sentence, 'Я буду гулять вокруг квартала в 19:30 в район у дома')


class HabitPaginationTestCase(HabitBaseTestCase):
    """Пять привычек на страницу."""

    def setUp(self):
        super().setUp()
        for number in range(10):
            Habit.objects.create(
                user=self.owner, action=f'привычка {number}',
                time=time(6, 0), place='дома',
            )
        self.url = reverse('habits:habit-list')

    def test_response_has_pagination_keys(self):
        data = self.client.get(self.url).json()

        for key in ('count', 'next', 'previous', 'results'):
            self.assertIn(key, data)

    def test_five_habits_per_page(self):
        data = self.client.get(self.url).json()

        self.assertEqual(data['count'], 12)
        self.assertEqual(len(data['results']), 5)
        self.assertIsNotNone(data['next'])

    def test_limit_and_offset(self):
        data = self.client.get(self.url, {'limit': 3, 'offset': 10}).json()

        self.assertEqual(len(data['results']), 2)
        self.assertIsNone(data['next'])
        self.assertIsNotNone(data['previous'])

    def test_limit_is_capped(self):
        data = self.client.get(self.url, {'limit': 10_000}).json()
        self.assertLessEqual(len(data['results']), 100)


class PublicHabitsTestCase(HabitBaseTestCase):
    """Витрина публичных привычек."""

    def setUp(self):
        super().setUp()
        self.public = Habit.objects.create(
            user=self.stranger, action='пить воду утром', time=time(8, 0),
            place='кухня', is_public=True,
        )
        Habit.objects.create(
            user=self.stranger, action='секретная привычка', time=time(8, 0), place='кухня',
        )
        self.url = reverse('habits:habit-public')

    def test_anonymous_has_no_access(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_only_public_habits_are_listed(self):
        data = self.client.get(self.url).json()

        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['action'], 'пить воду утром')

    def test_author_is_not_exposed(self):
        item = self.client.get(self.url).json()['results'][0]
        self.assertNotIn('user', item)

    def test_list_is_read_only(self):
        response = self.client.post(self.url, {
            'action': 'взлом', 'time': '10:00:00', 'place': 'нигде',
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_public_habit_of_other_user_still_not_editable(self):
        url = reverse('habits:habit-detail', args=(self.public.pk,))
        self.assertEqual(self.client.patch(url, {'action': 'взлом'}).status_code, status.HTTP_404_NOT_FOUND)

    def test_public_list_is_paginated(self):
        data = self.client.get(self.url).json()
        self.assertIn('results', data)
