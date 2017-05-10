from unittest import TestCase

from generator.exceptions import DeadlockInGenerationError, NotPossibleToGenerateSosError
from generator.generator import Generator
from generator.model import Member
from generator.integration.mock import MockWorkDaysService, MockClosedDaysDAO, MockDrygDAO


class TestGenerator(TestCase):

    @property
    def _basic_mock_work_day_service(self):
        return MockWorkDaysService(start_after_date="2017-01-02",
                                   closed_days_dao=MockClosedDaysDAO(),
                                   dryg_dao=MockDrygDAO())

    @property
    def _large_list_of_members(self):
        members = []
        for index, name in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ1234567890"):
            members.append(Member(first_name=name, sos_percentage=50, family=index))
        return members

    def test_generator_proportion_100_gives_two_sos(self):
        m = Member()
        m.sos_percentage = 100
        generator = Generator([m], self._basic_mock_work_day_service)
        generator._populate_pot()
        self.assertEqual(len(generator.pot), 2)

    def test_generator_proportion_50_gives_one_sos(self):
        m = Member()
        m.sos_percentage = 50
        generator = Generator([m], self._basic_mock_work_day_service)
        generator._populate_pot()
        self.assertEqual(len(generator.pot), 1)

    def test_generator_proportion_0_gives_no_sos(self):
        m = Member()
        m.sos_percentage = 0
        generator = Generator([m], self._basic_mock_work_day_service)
        self.assertEqual(len(generator.pot), 0)

    def test_list_is_random(self):
        names_ordered = "ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ"
        members = []
        for index, name in enumerate(names_ordered):
            members.append(Member(first_name=name, sos_percentage=50, family=index))

        generator = Generator(members, self._basic_mock_work_day_service)
        generator.generate()
        names = ""
        for day in generator.sos_days:
            for m in day.members:
                names += m.first_name
        self.assertNotEqual(names, names_ordered)

    def test_members_family_not_allowed_more_than_once_in_holy_period(self):
        m1 = Member(family=1)
        m2 = Member(family=1)
        m3 = Member(family=1)
        generator = Generator([m1, m2, m3], self._basic_mock_work_day_service)
        generator.sos_days.append_member(m1)
        generator.sos_days.append_member(m2)
        self.assertTrue(generator._is_members_family_in_holy_period(m3))

    def test_sponsor_is_on_same_day_as_sponsored(self):
        sponsor = Member(first_name="sponsor", sos_percentage=50, family=100, sponsor_for_family=200)
        sponsored = Member(first_name="sponsored", sos_percentage=50, family=200)

        members = self._large_list_of_members
        members.extend([sponsor, sponsored])
        generator = Generator(members, self._basic_mock_work_day_service, sponsor_holy_period_length=0)

        generator.generate()
        sos_days = generator.sos_days
        was_found = False
        for day in sos_days:
            if sponsor in day.members:
                self.assertTrue(sponsored in day.members)
                was_found = True
        self.assertTrue(was_found)

    def test_generator_retries_if_deadlock_occurs(self):
        m1 = Member(family=1)
        m2 = Member(family=1)
        generator = Generator([m1, m2], self._basic_mock_work_day_service)
        with self.assertRaises(NotPossibleToGenerateSosError):
            generator.generate()
        self.assertEqual(generator.number_of_retries_done, 1000)

    def test_sponsors_are_always_picked_first(self):
        sponsor = Member(first_name="sponsor", sos_percentage=50, family=100, sponsor_for_family=200)
        sponsored = Member(first_name="sponsored", sos_percentage=50, family=200)

        members = self._large_list_of_members
        members.extend([sponsor, sponsored])
        generator = Generator(members, self._basic_mock_work_day_service)
        generator.generate()
        first_day = generator.sos_days[0]
        self.assertTrue(sponsor in first_day.members)
        self.assertTrue(sponsored in first_day.members)

    def test_sponsor_is_picked_direct_after_holy_period(self):
        sponsor = Member(first_name="sponsor", sos_percentage=100, family=100, sponsor_for_family=200)
        sponsored = Member(first_name="sponsored", sos_percentage=100, family=200, sponsored_by_family=100)

        sponsor_holy_period_length = 10

        members = self._large_list_of_members
        members.extend([sponsor, sponsored])
        generator = Generator(members, self._basic_mock_work_day_service,
                              holy_period_length=1, sponsor_holy_period_length=sponsor_holy_period_length)
        generator.generate()

        first_day = generator.sos_days[0]
        self.assertTrue(sponsor in first_day.members)
        self.assertTrue(sponsored in first_day.members)

        day_after_sponsor_holy_period = generator.sos_days[sponsor_holy_period_length + 1]
        self.assertTrue(sponsor in day_after_sponsor_holy_period.members)
        self.assertTrue(sponsored in day_after_sponsor_holy_period.members)

    def test_sponsored_with_higher_proportion_than_sponsor_still_gets_sos(self):
        sponsor1 = Member(sos_percentage=50, family=100, sponsor_for_family=200)
        sponsor2 = Member(sos_percentage=50, family=100, sponsor_for_family=200)
        sponsored1 = Member(sos_percentage=100, family=200, sponsored_by_family=100)
        sponsored2 = Member(sos_percentage=100, family=200, sponsored_by_family=100)

        members = [sponsor1, sponsor2, sponsored1, sponsored2]
        generator = Generator(members, self._basic_mock_work_day_service,
                              sponsor_holy_period_length=0, holy_period_length=0)
        generator.generate()
        self.assertEqual(generator.sos_days.members.count(sponsor1), 1)
        self.assertEqual(generator.sos_days.members.count(sponsor2), 1)
        self.assertEqual(generator.sos_days.members.count(sponsored1), 2)
        self.assertEqual(generator.sos_days.members.count(sponsored2), 2)

    def test_member_is_not_allowed_to_have_sos_in_end_grace_period(self):
        m1 = Member(sos_percentage=50, family=1)
        m2 = Member(sos_percentage=50, family=2)
        m3 = Member(sos_percentage=50, family=3, end_date="2017-01-03")
        generator = Generator([m1, m2, m3], self._basic_mock_work_day_service,
                              sponsor_holy_period_length=0, holy_period_length=0)
        generator.sos_days.append_member(m1)
        generator.sos_days.append_member(m2)
        generator.sos_days.append_member(m3)
        self.assertFalse(m3 in generator.sos_days.members)

    def test_last_day_is_full(self):
        m = Member(sos_percentage=50, family=1)
        generator = Generator([m], self._basic_mock_work_day_service,
                              sponsor_holy_period_length=0, holy_period_length=0)
        generator.generate()
        self.assertListEqual([], generator.sos_days)
