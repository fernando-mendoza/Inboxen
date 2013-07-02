##
#
# Copyright 2013 Jessica Tallon, Matt Molyneaux
# 
# This file is part of Inboxen.
#
# Inboxen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Inboxen is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Inboxen.  If not, see <http://www.gnu.org/licenses/>.
#
##

from datetime import datetime
from pytz import utc
import logging

from inboxen.models import Alias, Attachment, Email, Header
from config.settings import datetime_format, recieved_header_name
from django.db import transaction
from dateutil import parser

@transaction.commit_on_success
def make_email(message, alias, domain):
    """Push message to the database.

    Will throw an Alias.DoesNotExist exception if alias and domain are not valid"""

    try:
        inbox = Alias.objects.get(alias=alias, domain__domain=domain, deleted=False)
    except Alias.DoesNotExist, e:
        logging.debug("No alias: %s" % e)
        return # alias deleted while msg was in queue

    user = inbox.user
    body = message.base.body
    try:
        recieved_date = parser.parse(message[recieved_header_name])
    except (AttributeError, KeyError):
        logging.debug("No %s header in message, creating new timestamp" % recieved_header_name)
        recieved_date = datetime.now(utc)

    email = Email(inbox=inbox, user=user, body=body, recieved_date=recieved_date)
    email.save()

    message['Content-Type'] = message.base.content_encoding['Content-Type'][0] or 'text/plain'
    message['Content-Disposition'] = message.base.content_encoding['Content-Disposition'][0] or ''

    head_list = []

    for name in message.keys():
        header = Header(name=name, data=message[name])
        header.save()
        head_list.append(header)
    # add all the headers at once should save us some queries
    email.headers.add(*head_list)

    attach_list = []
    for part in message.walk():
        if not part.body:
            part.body = u''
        attachment = Attachment(
                        content_type=part.content_encoding['Content-Type'][0],
                        content_disposition=part.content_encoding['Content-Disposition'][0],
                        data=part.body
                        )
        attachment.save()
        attach_list.append(attachment)
    # as with headers above
    email.attachments.add(*attach_list)
