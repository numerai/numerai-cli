const AWS = require('aws-sdk');
const util = require('util');

function runTask(ecs_client, ecs_cluster, ecs_arn, subnet, security_group) {
    // run an ECS Fargate task
    const params = {
        cluster: `${ecs_cluster}`,
        launchType: 'FARGATE',
        taskDefinition: `${ecs_arn}`,
        networkConfiguration: {
            awsvpcConfiguration: {
                subnets: [
                    `${subnet}`,
                ],
                assignPublicIp: "ENABLED",
                securityGroups: [
                    `${security_group}`,
                ],
            },
        },
    };
    console.log("running task with taskDefinition:", params.taskDefinition);
    const taskStart = await ecs.runTask(params).promise();

    console.log("started :", );

    const message = {
        task: taskStart.tasks[0].taskArn
        status: "pending"
    };
    return message
}

exports.handler = async (event) => {
    const ecs = new AWS.ECS();

    message = []
    for (task_arn in process.env.ecs_task_arns) {
        message.push(runTask(ecs, process.env.ecs_cluster, task_arn, process))
    }

    return {
        statusCode: 200,
        body: JSON.stringify(message)
    };
};
