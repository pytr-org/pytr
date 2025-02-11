from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


class TimelineDetailV2(TypedDict):
    """
    Incomplete typed representation of the TR `timelineDetailV2` object.
    """

    id: str
    sections: list[TimelineDetailV2_Section]


class TimelineDetailV2_Section(TypedDict):
    title: str
    type: Literal["header", "table", "steps"]
    data: dict[str, Any] | list[dict[str, Any]]


class TimelineDetailV2_CustomerSupportChatAction(TypedDict):
    type: Literal["customerSupportChat"]
    payload: TimelineDetailV2_CustomerSupportChatAction_Payload
    style: str
    type: str


class TimelineDetailV2_CustomerSupportChatAction_Payload(TypedDict):
    contextParams: TimelineDetailV2_CustomerSupportChatAction_ContextParamms
    contextCategory: str


class TimelineDetailV2_CustomerSupportChatAction_ContextParamms(TypedDict):
    chat_flow_key: str
    timelineEventId: str
    savingsPlanId: NotRequired[str]
    primId: NotRequired[str]
    groupId: NotRequired[str]
    createdAt: NotRequired[str]
    amount: NotRequired[str]
    iban: NotRequired[str]
    interestPayoutId: NotRequired[str]
