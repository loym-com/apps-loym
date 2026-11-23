from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOfferingSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env.ref("account_offering.journal_offering")
        tag = cls.env.ref("account_offering.account_tag_default_offering")
        offering_tag = cls.env.ref("account_offering.account_tag_offering")
        cls.accounts = cls.env["account.account"].create([
            {
                "name": "Offering asset",
                "code": "100001",
                "account_type": "asset_current",
                "tag_ids": [Command.set([tag.id, offering_tag.id])],
            },
            {
                "name": "Offering income",
                "code": "400001",
                "account_type": "income",
                "tag_ids": [Command.set([tag.id, offering_tag.id])],
            },
        ])
        cls.other_journal = cls.env["account.journal"].create({
            "name": "Other journal",
            "code": "OTHER",
            "type": "general",
        })
        cls.user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Offering user",
            "login": "offering-security-test",
            "group_ids": [Command.set([cls.env.ref("account_offering.group_offering_user").id])],
        })
        cls.other_move = cls.env["account.move"].create({
            "journal_id": cls.other_journal.id,
            "line_ids": [
                Command.create({"account_id": cls.accounts[0].id, "debit": 1}),
                Command.create({"account_id": cls.accounts[1].id, "credit": 1}),
            ],
        })

    def test_account_and_tag_read_access(self):
        self.env.ref("account.access_account_account_user").active = False
        self.env.ref("account.access_account_tag_internal_user").active = False
        accounts = self.accounts.with_user(self.user)
        tag = self.env.ref("account_offering.account_tag_offering").with_user(self.user)
        self.assertEqual(len(accounts.read(["name", "tag_ids"])), 2)
        self.assertEqual(tag.read(["name"])[0]["name"], "Offering")
        with self.assertRaises(AccessError), self.cr.savepoint():
            accounts[0].write({"name": "Changed account"})
        with self.assertRaises(AccessError), self.cr.savepoint():
            tag.write({"name": "Changed tag"})

    def test_registration_and_journal_isolation(self):
        self.assertFalse(self.user.has_group("account.group_account_invoice"))
        user_env = self.env(user=self.user)
        self.assertFalse(user_env["account.journal"].search([("id", "=", self.other_journal.id)]))
        self.assertFalse(user_env["account.move"].search([("id", "=", self.other_move.id)]))
        self.assertFalse(user_env["account.move.line"].search([("move_id", "=", self.other_move.id)]))
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.other_move.with_user(self.user).read(["ref"])
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.other_move.with_user(self.user).write({"ref": "Forbidden"})
        with self.assertRaises(AccessError), self.cr.savepoint():
            user_env["account.move"].create({"journal_id": self.other_journal.id})

        action = self.env.ref("account_offering.action_account_offering").with_user(self.user).run()
        move = user_env["account.move"].browse(action["res_id"])
        self.assertEqual(move.journal_id, self.journal)
        self.assertEqual(action["views"], [
            [self.env.ref("account_offering.view_account_move_form_offering").id, "form"],
        ])
        self.assertEqual(action["target"], "current")
        self.assertEqual(len(move.line_ids), 2)
        move.write({"ref": "Updated offering"})
        with self.assertRaises((AccessError, UserError)), self.cr.savepoint():
            move.write({"journal_id": self.other_journal.id})
        with self.assertRaises((AccessError, UserError)), self.cr.savepoint():
            move.line_ids[0].write({"move_id": self.other_move.id})
        empty_move = user_env["account.move"].create({"journal_id": self.journal.id})
        with self.assertRaises((AccessError, UserError)), self.cr.savepoint():
            empty_move.write({"journal_id": self.other_journal.id})
        user_env["account.move"].get_views([
            (self.env.ref("account_offering.view_account_move_form_offering").id, "form"),
        ])
