from __future__ import absolute_import, print_function

import pprint

from twisted.internet import defer

from buildbot.process.properties import Properties
from buildbot.process.results import statusToString
from buildbot.reporters import http, utils
from buildbot.util import httpclientservice
from buildbot.util.logger import Logger

logger = Logger()

STATUS_EMOJIS = {
    "success": ":sunglassses:",
    "warnings": ":meow_wow:",
    "failure": ":skull:",
    "skipped": ":slam:",
    "exception": ":skull:",
    "retry": ":facepalm:",
    "cancelled": ":slam:",
}
STATUS_COLORS = {
    "success": "#36a64f",
    "warnings": "#fc8c03",
    "failure": "#fc0303",
    "skipped": "#fc8c03",
    "exception": "#fc0303",
    "retry": "#fc8c03",
    "cancelled": "#fc8c03",
}
DEFAULT_HOST = "https://hooks.slack.com"  # deprecated


class SlackStatusPush(http.HttpStatusPush):
    name = "SlackStatusPush"
    neededDetails = dict(wantProperties=True)

    def checkConfig(
        self, endpoint, channel=None, host_url=None, username=None, **kwargs
    ):
        if not isinstance(endpoint, str):
            logger.warning(
                "[SlackStatusPush] endpoint should be a string, got '%s' instead",
                type(endpoint).__name__,
            )
        elif not endpoint.startswith("http"):
            logger.warning(
                '[SlackStatusPush] endpoint should start with "http...", endpoint: %s',
                endpoint,
            )
        if channel and not isinstance(channel, str):
            logger.warning(
                "[SlackStatusPush] channel must be a string, got '%s' instead",
                type(channel).__name__,
            )
        if username and not isinstance(username, str):
            logger.warning(
                "[SlackStatusPush] username must be a string, got '%s' instead",
                type(username).__name__,
            )
        if host_url and not isinstance(host_url, str):  # deprecated
            logger.warning(
                "[SlackStatusPush] host_url must be a string, got '%s' instead",
                type(host_url).__name__,
            )
        elif host_url:
            logger.warning(
                "[SlackStatusPush] argument host_url is deprecated and will be removed in the next release: specify the full url as endpoint"
            )

    @defer.inlineCallbacks
    def reconfigService(
        self,
        endpoint,
        channel=None,
        host_url=None,  # deprecated
        username=None,
        attachments=True,
        verbose=False,
        **kwargs
    ):

        yield super().reconfigService(serverUrl=endpoint, **kwargs)
        if host_url:
            logger.warning(
                "[SlackStatusPush] argument host_url is deprecated and will be removed in the next release: specify the full url as endpoint"
            )
        self.endpoint = endpoint
        self.channel = channel
        self.username = username
        self.attachments = attachments
        self._http = yield httpclientservice.HTTPClientService.getService(
            self.master,
            self.endpoint,
            debug=self.debug,
            verify=self.verify,
        )
        self.verbose = verbose
        self.project_ids = {}

    @defer.inlineCallbacks
    def sendMessage(self, reports):
        for report in reports:
            builds = report["builds"]
            for build in builds:
                pprint.pprint(build)
                msg = ""

                scheduler = build["properties"]["scheduler"][0]
                msg += f"Scheduler: {scheduler}\n"

                builder = build["properties"]["buildername"][0]
                msg += f"Builder: {builder}\n"

                worker = build["properties"]["workername"][0]
                msg += f"Worker: {worker}\n"

                reason = build["buildset"]["reason"]
                msg += f"Reason: {reason}\n"

                state_string = build["state_string"]
                msg += f"State: {state_string}\n"

                branch = build["properties"].get("branch")
                if branch is not None:
                    msg += f"Branch: {branch[0]}\n"

                pr_url = build["properties"].get("pullrequesturl")
                if pr_url is not None:
                    msg += pr_url[0]
                    msg += "\n\n"

                url = build["url"]
                msg += url
                msg += "\n\n"

                users = build.get("users")
                if users is not None:
                    msg += str(users)
                    msg += "\n\n"

                msg += "\n\n"

                try:
                    postData = {"text": msg}
                    response = yield self._http.post("", json=postData)
                    if response.code != 200:
                        content = yield response.content()
                        logger.error(
                            "[SlackStatusPush] {code}: unable to upload status: {content}",
                            code=response.code,
                            content=content,
                        )
                except Exception as e:
                    logger.error("[SlackStatusPush] Failed to send status: {error}", error=e)
