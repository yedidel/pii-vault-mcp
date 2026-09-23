package bridge

internal object FillFormParameterPolicy {

    fun validate(
        actionType: String,
        parameters: Map<String, String>,
    ): String? {
        if (actionType.uppercase() != "FILL_FORM") return null

        for (key in listOf("email", "password")) {
            val value = parameters[key]?.trim().orEmpty()
            if (value.isNotEmpty() && !isAllowedFillFormRef(value)) {
                return (
                    "Sensitive parameter '$key' must be a vault reference " +
                        "(vault://pii/... or vault://field/...)"
                    )
            }
        }
        return null
    }

    internal fun isAllowedFillFormRef(value: String): Boolean {
        return value.startsWith("vault://pii/") || value.startsWith("vault://field/")
    }
}
