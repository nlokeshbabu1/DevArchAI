import { AwsFinding } from '../api/endpoints/aws'

function regionFor(finding: AwsFinding) {
  return finding.region && finding.region !== 'aws-global' ? finding.region : 'us-east-1'
}

function encoded(value?: string | null) {
  return encodeURIComponent(value || '')
}

export function generateAWSConsoleLink(finding: AwsFinding): string | null {
  const resourceType = (finding.resource_type || '').toLowerCase()
  const title = finding.title.toLowerCase()
  const resourceId = finding.resource_id || ''
  const region = regionFor(finding)

  if (title.includes('root') || title.includes('mfa')) {
    return 'https://console.aws.amazon.com/iam/home#/security_credentials'
  }

  if (resourceType.includes('security_group')) {
    return `https://${region}.console.aws.amazon.com/ec2/home?region=${region}#SecurityGroups:groupId=${encoded(resourceId)}`
  }

  if (resourceType.includes('eks')) {
    return `https://${region}.console.aws.amazon.com/eks/home?region=${region}#/clusters/${encoded(resourceId)}`
  }

  if (resourceType.includes('iam_user')) {
    return `https://console.aws.amazon.com/iam/home#/users/details/${encoded(resourceId)}`
  }

  if (resourceType.includes('iam_role')) {
    return `https://console.aws.amazon.com/iam/home#/roles/details/${encoded(resourceId)}`
  }

  if (resourceType.includes('s3')) {
    return `https://s3.console.aws.amazon.com/s3/buckets/${encoded(resourceId)}`
  }

  if (resourceType.includes('ec2')) {
    return `https://${region}.console.aws.amazon.com/ec2/home?region=${region}#InstanceDetails:instanceId=${encoded(resourceId)}`
  }

  if (resourceType.includes('lambda')) {
    return `https://${region}.console.aws.amazon.com/lambda/home?region=${region}#/functions/${encoded(resourceId)}`
  }

  if (resourceType.includes('rds')) {
    return `https://${region}.console.aws.amazon.com/rds/home?region=${region}#database:id=${encoded(resourceId)};is-cluster=false`
  }

  if (resourceType.includes('ebs_volume')) {
    return `https://${region}.console.aws.amazon.com/ec2/home?region=${region}#VolumeDetails:volumeId=${encoded(resourceId)}`
  }

  return null
}
