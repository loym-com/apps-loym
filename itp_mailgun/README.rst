=========
 Mailgun
=========

The module allows to receive incoming messages or send them to clients who uses external mail services (e.g. gmail.com) by using Mailgun.
There is no IMAP or POP3 servers on mailgun that is to be used with odoo.
That is why we need this module. It fetches messages from mailgun using their API and stores them in odoo.

TODO
====

* If emails are sent when odoo is stopped then Mailgun will retry (other than for delivery notification) during 8 hours at the following intervals before stop trying: 10 minutes, 10 minutes, 15 minutes, 30 minutes, 1 hour, 2 hour and 4 hours. This could be fixed by fetching undelivered messages after odoo starts.

Questions?
==========

To get an assistance on this module contact us by email :arrow_right: it@it-projects.info

Contributors
============

* Ildar Nasyrov <apps@it-projects.info>
* Ivan Yelizariev <apps@it-projects.info>
