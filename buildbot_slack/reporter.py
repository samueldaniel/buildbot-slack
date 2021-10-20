# Based on the gitlab reporter from buildbot

from __future__ import absolute_import, print_function

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
                msg = ""
                reason = build["buildset"]["reason"]
                state_string = build["state_string"]
                results = build["results"]
                url = build["url"]
                branch = build["properties"].get("branch", "")
                pr_url = build["properties"].get("pullrequesturl", "")
                users = build.get("users", "")
                msg += f"{state_string} - {branch} - {reason}"
                msg += "\n"
                if results:
                    msg += results
                    msg += "\n"
                if pr_url:
                    msg += pr_url
                    msg += "\n"
                msg += url
                msg += "\n"
                msg += users
                msg += "\n"
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
