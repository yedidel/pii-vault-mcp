package continuation

/**
 * supported connector types.
 *
 * each connector defines how a workflow continuation is delivered.
 */
enum class ConnectorType {

    /**
     * agent polls for updates.
     */
    POLLING,

    /**
     * continue using a live communication channel.
     */
    CHANNEL,

    /**
     * continue using an existing conversation.
     */
    THREAD,

    /**
     * continue using an http callback.
     */
    WEBHOOK,
}