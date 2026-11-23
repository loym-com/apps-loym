import ast
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
        if xmlid.endswith("view_account_move_form_offering"):
            return SimpleNamespace(id=44)
        if xmlid == "account_offering.journal_offering":
            return SimpleNamespace(id=55)
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
        return context.get("action")

    def test_new_opens_created_entry_without_clearing_breadcrumbs(self):
        env = FakeEnv(["asset", "income"])
        action = self.run_action(env)
        self.assertEqual(action, {
            "type": "ir.actions.act_window",
            "name": "Offering",
            "res_model": "account.move",
            "views": [[44, "form"]],
            "res_id": 123,
            "target": "current",
        })

    def test_both_views_use_the_server_action_for_new(self):
        views_file = ACTION_FILE.parents[1] / "views/account_move_views.xml"
        tree = ElementTree.parse(views_file)
        for view_type in ("list", "form"):
            with self.subTest(view_type=view_type):
                view = tree.find(
                    f".//record[@id='view_account_move_{view_type}_offering']"
                    f"/field[@name='arch']/{view_type}"
                )
                self.assertEqual(view.get("create"), "0")
                button = view.find("./header/button[@string='New']")
                self.assertEqual(button.get("type"), "action")
                self.assertEqual(button.get("name"), "%(account_offering.action_account_offering)d")

    def test_balanced_entries_with_equal_and_unequal_account_counts(self):
        for account_types in (
            ["asset", "income"],
            ["asset", "expense", "expense", "income"],
            ["asset", "income", "liability", "equity"],
        ):
            with self.subTest(account_types=account_types):
                env = FakeEnv(account_types)
                self.run_action(env)
                lines = env.created[0]["line_ids"]
                self.assertEqual(env.created[0]["journal_id"], 55)
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

    def test_window_action_filters_offering_journal(self):
        menu_file = ACTION_FILE.parents[1] / "views/account_offering_menus.xml"
        domain = ElementTree.parse(menu_file).find(
            ".//record[@id='action_offering_moves']/field[@name='domain']"
        ).get("eval")
        refs = {"account_offering.journal_offering": 55}
        expression = eval(domain, {"__builtins__": {"str": str}}, {"ref": refs.__getitem__})
        self.assertEqual(ast.literal_eval(expression), [("journal_id", "=", 55)])


if __name__ == "__main__":
    unittest.main()
