const AWS = require('aws-sdk');
const util = require('util');


exports.handler = async (event) => {
    const ecs = new AWS.ECS();

    let messages = []
    let task_arns = JSON.parse(process.env.ecs_task_arns)
    for (let task_arn of task_arns) {
        // run an ECS Fargate task
        const params = {
            cluster: `${process.env.ecs_cluster}`,
            launchType: 'FARGATE',
            taskDefinition: `${task_arn}`,
            networkConfiguration: {
                awsvpcConfiguration: {
                    subnets: [
                        `${process.env.subnet}`,
                    ],
                    assignPublicIp: "ENABLED",
                    securityGroups: [
                        `${process.env.security_group}`,
                    ],
                },
            },
        };
        console.log("running task with taskDefinition:", params.taskDefinition);
        const taskStart = await ecs.runTask(params).promise();

        console.log("started :", );

        const message = {
            task: taskStart.tasks[0].taskArn,
            status: "pending"
        };
        messages.push(message)
    }

    return {
        statusCode: 200,
        body: JSON.stringify(messages)
    };
};
