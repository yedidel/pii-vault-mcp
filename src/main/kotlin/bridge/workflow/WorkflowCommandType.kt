package bridge.workflow

/**
 * Identifies workflow commands that have external side effects.
 *
 * Used to prevent executing the same command more than once
 * after Kafka retries or application recovery.
 */
enum class WorkflowCommandType {

    VERIFY_AGENT,

    REQUEST_VAULT,

    NOTIFY_AGENT,

    UPDATE_ACTION_STATUS,

    PUBLISH_EVENT,

    TRANSITION
}