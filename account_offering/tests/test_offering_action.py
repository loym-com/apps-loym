import datetime
import unittest
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree


ACTION_FILE = Path(__file__).resolve().parents[1] / "data/ir_actions_server_data.xml"


class UserError(Exception):
    pass


class FakeEnv:
    def __init__(self, account_types, lang="en_US"):
        self.accounts = [
            SimpleNamespace(id=index, internal_group=group)
            for index, group in enumerate(account_types, 1)
        ]
        self.user = SimpleNamespace(tz="UTC")
        self.created = []
        self.lang = lang

    def ref(self, xmlid):
        if xmlid.endswith("menu_account_offering"):
            return SimpleNamespace(name="Offering")
        if xmlid.endswith("view_account_move_list_offering"):
            return SimpleNamespace(id=43)
        return SimpleNamespace(id=42, ids=[42])

    def __getitem__(self, model):
        if model == "account.account":
            return SimpleNamespace(search=lambda domain: self.accounts)
        if model == "account.move":
            return SimpleNamespace(create=self.create)
        if model == "ir.qweb":
            return SimpleNamespace(_render=self.render)
        raise KeyError(model)

    def render(self, template):
        if template != "account_offering.error_missing_default_accounts":
            raise KeyError(template)
        return {
            "en_US": "Configure at least one debit account and one credit account with the Default offering tag.",
            "nb_NO": "Merk minst én debetkonto og én kreditkonto med Standard kollekt.",
        }[self.lang]

    def create(self, values):
        self.created.append(values)
        return SimpleNamespace(id=123)


class OfferingActionTest(unittest.TestCase):
    def run_action(self, env):
        code = ElementTree.parse(ACTION_FILE).find(
            ".//record[@id='action_account_offering']/field[@name='code']"
        ).text
        context = {
            "env": env,
            "datetime": datetime,
            "timezone": lambda name: datetime.timezone.utc,
            "Command": SimpleNamespace(create=lambda values: values),
            "UserError": UserError,
        }
        exec(compile(code, str(ACTION_FILE), "exec"), context)
        return context["action"]

    def test_balanced_entries_with_equal_and_unequal_account_counts(self):
        for account_types in (
            ["asset", "income"],
            ["asset", "expense", "expense", "income"],
            ["asset", "income", "liability", "equity"],
        ):
            with self.subTest(account_types=account_types):
                env = FakeEnv(account_types)
                action = self.run_action(env)
                lines = env.created[0]["line_ids"]
                debit = sum(line.get("debit", 0) for line in lines)
                credit = sum(line.get("credit", 0) for line in lines)
                self.assertEqual(debit, credit)
                self.assertEqual(debit, max(
                    sum(t in ("asset", "expense") for t in account_types),
                    sum(t not in ("asset", "expense") for t in account_types),
                ))
                self.assertCountEqual(
                    [line["account_id"] for line in lines],
                    range(1, len(account_types) + 1),
                )
                for line in lines:
                    group = account_types[line["account_id"] - 1]
                    side = "debit" if group in ("asset", "expense") else "credit"
                    other_side = "credit" if side == "debit" else "debit"
                    self.assertGreaterEqual(line[side], 1)
                    self.assertEqual(line.get(other_side, 0), 0)
                self.assertEqual(action["res_id"], 123)
                self.assertEqual(action["view_mode"], "form,list")
                self.assertEqual(action["views"], [[42, "form"], [43, "list"]])

    def test_missing_side_does_not_create_move(self):
        for account_types in ([], ["asset", "expense"], ["income"]):
            with self.subTest(account_types=account_types):
                env = FakeEnv(account_types)
                with self.assertRaisesRegex(UserError, "at least one debit account"):
                    self.run_action(env)
                self.assertEqual(env.created, [])

    def test_missing_side_uses_rendered_language(self):
        env = FakeEnv([], lang="nb_NO")
        with self.assertRaisesRegex(UserError, "Merk minst én debetkonto"):
            self.run_action(env)
        self.assertEqual(env.created, [])


if __name__ == "__main__":
    unittest.main()
