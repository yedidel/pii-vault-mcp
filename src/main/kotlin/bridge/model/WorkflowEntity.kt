package bridge.model

import bridge.Bridge.StatusType
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.Table


@Entity
@Table(name = "workflows")
class WorkflowEntity (
    //primary key id of current work flow
    @Id
    @Column(name = "workflow_id", nullable = false)
    val workflowId: String,

    //request id
    @Column(name="request_id", nullable = false)
    val requestId: String,

    //platform of agent
    @Column(name="platform", nullable = false)
    val platform: String,

    //agent session id
    @Column(name="agent_session_id", nullable = false)
    var agentSessionId: String
    )