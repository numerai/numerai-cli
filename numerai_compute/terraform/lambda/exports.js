const AWS = require('aws-sdk');
const util = require('util');

exports.handler = async (event) => {
    const ecs = new AWS.ECS();

    // run an ECS Fargate task
    const params = {
        cluster: `${process.env.ecs_cluster}`,
        launchType: 'FARGATE',
        taskDefinition: `${process.env.ecs_arn}`,
        networkConfiguration: {
            awsvpcConfiguration: {
                subnets: [
                    `${process.env.ecs_subnet}`,
                ],
                assignPublicIp: "ENABLED",
                securityGroups: [
                    `${process.env.ecs_security_group}`,
                ],
            },
        },
    };
    console.log("running task with taskDefinition:", params.taskDefinition);
    const taskStart = await ecs.runTask(params).promise();

    console.log("started task ", JSON.stringify(taskStart));

    const message = { status: "pending" };
    // TODO: poll for a few minutes and check all submissions in numerapi

    return { statusCode: 200, body: JSON.stringify(message) };
};
