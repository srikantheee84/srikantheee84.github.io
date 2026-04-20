#!/bin/bash
# Deploy the Customer Feedback Pipeline to AWS
#
# Usage: ./deploy.sh <s3-bucket-name> [region] [environment]
#
# This script:
#   1. Packages Lambda functions into zip files
#   2. Uploads artifacts to S3
#   3. Deploys the CloudFormation stack
#   4. Prints the stack outputs

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <s3-bucket-name> [region] [environment]"
    echo ""
    echo "Examples:"
    echo "  $0 my-bucket"
    echo "  $0 my-bucket us-west-2 staging"
    exit 1
fi

S3_BUCKET="$1"
REGION="${2:-us-east-1}"
ENVIRONMENT="${3:-prod}"
STACK_NAME="customer-feedback-pipeline-${ENVIRONMENT}"

echo "============================================"
echo "  Customer Feedback Pipeline — Deploy"
echo "============================================"
echo ""
echo "S3 Bucket:    ${S3_BUCKET}"
echo "Region:       ${REGION}"
echo "Environment:  ${ENVIRONMENT}"
echo "Stack Name:   ${STACK_NAME}"
echo ""

# Step 1: Package Lambda functions
echo "[1/4] Packaging Lambda functions..."
PACKAGE_DIR=$(mktemp -d)
cp -r src/ "${PACKAGE_DIR}/src/"
cp requirements.txt "${PACKAGE_DIR}/"

# Install dependencies into the package
pip install -r requirements.txt -t "${PACKAGE_DIR}" --quiet 2>/dev/null || true

# Create zip
LAMBDA_ZIP="${PACKAGE_DIR}/lambda-package.zip"
(cd "${PACKAGE_DIR}" && zip -r "${LAMBDA_ZIP}" src/ -x "*.pyc" "*__pycache__*" > /dev/null)
echo "  Package created: $(du -h "${LAMBDA_ZIP}" | cut -f1)"

# Step 2: Upload to S3
echo ""
echo "[2/4] Uploading artifacts to S3..."
aws s3 cp "${LAMBDA_ZIP}" "s3://${S3_BUCKET}/customer-feedback-pipeline/lambda-package.zip" \
    --region "${REGION}" --quiet
echo "  Uploaded lambda-package.zip to s3://${S3_BUCKET}/customer-feedback-pipeline/"

# Upload CloudFormation template
aws s3 cp src/infra/template.yaml "s3://${S3_BUCKET}/customer-feedback-pipeline/template.yaml" \
    --region "${REGION}" --quiet
echo "  Uploaded template.yaml"

# Step 3: Deploy CloudFormation stack
echo ""
echo "[3/4] Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file src/infra/template.yaml \
    --stack-name "${STACK_NAME}" \
    --parameter-overrides \
        S3Bucket="${S3_BUCKET}" \
        Environment="${ENVIRONMENT}" \
    --capabilities CAPABILITY_IAM \
    --region "${REGION}" \
    --no-fail-on-empty-changeset

echo "  Stack deployed: ${STACK_NAME}"

# Step 4: Show outputs
echo ""
echo "[4/4] Stack outputs:"
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
    --output table 2>/dev/null || echo "  (no outputs defined yet)"

# Update Lambda code (CloudFormation doesn't always detect zip changes)
echo ""
echo "Updating Lambda function code..."
FUNCTIONS=$(aws cloudformation list-stack-resources \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query "StackResourceSummaries[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
    --output text 2>/dev/null || echo "")

for func in ${FUNCTIONS}; do
    aws lambda update-function-code \
        --function-name "${func}" \
        --s3-bucket "${S3_BUCKET}" \
        --s3-key "customer-feedback-pipeline/lambda-package.zip" \
        --region "${REGION}" \
        --no-cli-pager > /dev/null 2>&1 || true
    echo "  Updated: ${func}"
done

# Cleanup
rm -rf "${PACKAGE_DIR}"

echo ""
echo "============================================"
echo "  Deployment complete!"
echo "============================================"
echo ""
echo "Tear down:"
echo "  aws cloudformation delete-stack --stack-name ${STACK_NAME} --region ${REGION}"
