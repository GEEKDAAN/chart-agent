DIMENSION_DATE = "date"
DIMENSION_REGION = "region"
DIMENSION_CHANNEL = "channel"

DIMENSION_LABELS = {
    DIMENSION_DATE: "日期趋势",
    DIMENSION_REGION: "各地区",
    DIMENSION_CHANNEL: "各渠道",
}

DIMENSION_KEYWORDS = {
    DIMENSION_DATE: ("趋势", "每天", "每日", "日期", "按天", "折线"),
    DIMENSION_REGION: ("各地区", "按地区", "分地区", "地区分布"),
    DIMENSION_CHANNEL: ("各渠道", "按渠道", "分渠道", "渠道分布"),
}

DECISION_DIMENSION_KEYWORDS = {
    DIMENSION_REGION: ["各地区", "按地区", "分地区", "地区分布"],
    DIMENSION_CHANNEL: ["各渠道", "按渠道", "分渠道", "渠道分布"],
    DIMENSION_DATE: ["趋势", "日期", "每天", "每日", "按天", "近30天", "最近30天", "近7天", "最近7天"],
}

REGION_VALUES = ("华东", "华南", "华北")
CHANNEL_VALUES = ("抖音", "小红书", "微信", "天猫")
