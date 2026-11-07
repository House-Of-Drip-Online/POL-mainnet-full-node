#!/usr/bin/env python3
"""Create/review/execute the standalone node CloudFormation change set.

Root deployment requires an explicit owner-authorized exception flag. The
default remains non-root. This controller never deletes resources or grants LIVE.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parent


def assert_deployer(identity,account,*,owner_authorized_root=False):
    if identity.get('Account')!=account:raise ValueError('AWS_ACCOUNT_MISMATCH')
    arn=identity.get('Arn','')
    if arn.endswith(':root'):
        if owner_authorized_root:return
        raise ValueError('ROOT_DEPLOYMENT_REQUIRES_EXPLICIT_OWNER_AUTHORIZATION')
    if not re.fullmatch(r'arn:aws:(sts|iam)::'+re.escape(account)+r':(assumed-role|user)/.+',arn):
        raise ValueError('NONROOT_DEPLOYMENT_IDENTITY_REQUIRED')


def assert_nondestructive(changes):
    for change in changes:
        resource=change.get('ResourceChange',{})
        if resource.get('Action') not in ('Add','Modify') or resource.get('Replacement') in ('True','Conditional'):
            raise ValueError('DESTRUCTIVE_OR_UNCERTAIN_CHANGE_REQUIRES_REVIEW')


def monthly_base_cost():
    # AWS Pricing GetProducts, us-east-1, observed 2026-11-06; not a quote guarantee.
    costs={'compute':730*0.8064,'dataStorage':8192*.08,'rootStorage':64*.08,
           'extraIops':(16000-3000)*.005,'extraThroughput':(1000-125)*.04,
           'publicIpv4':730*.005}
    return {**costs,'total':sum(costs.values()),'excludes':['transfer','monitoring','backups','tax']}


def preflight(session,settings,commit):
    ec2=session.client('ec2')
    identity=session.client('sts').get_caller_identity()
    subnet=ec2.describe_subnets(SubnetIds=[settings['SubnetId']])['Subnets'][0]
    if subnet['VpcId']!=settings['VpcId'] or subnet['AvailabilityZone']!=settings['AvailabilityZone']:
        raise ValueError('SUBNET_VPC_OR_AZ_MISMATCH')
    image=ec2.describe_images(ImageIds=[settings['ImageId']])['Images'][0]
    if (image['OwnerId']!='099720109477' or image['Architecture']!='x86_64'
        or image['State']!='available' or 'ubuntu-noble-24.04-amd64-server' not in image['Name']):
        raise ValueError('UNVERIFIED_UBUNTU_AMI')
    tables=ec2.describe_route_tables(Filters=[{'Name':'vpc-id','Values':[settings['VpcId']]}])['RouteTables']
    route=next((t for t in tables if any(a.get('SubnetId')==settings['SubnetId'] for a in t['Associations'])),None)
    if route is None:route=next(t for t in tables if any(a.get('Main') for a in t['Associations']))
    if not any(r.get('DestinationCidrBlock')=='0.0.0.0/0' and r.get('GatewayId','').startswith('igw-')
               and r.get('State')=='active' for r in route['Routes']):
        raise ValueError('PUBLIC_P2P_SUBNET_REQUIRES_IGW_ROUTE')
    template=(ROOT/'aws/node.yaml').read_text()
    session.client('cloudformation').validate_template(TemplateBody=template)
    return {'sourceCommit':commit,'identity':{'Account':identity['Account'],'Arn':identity['Arn']},
            'templateSha256':hashlib.sha256(template.encode()).hexdigest(),
            'baseMonthlyUsd':monthly_base_cost(),'region':session.region_name,
            'nodeReady':False,'executionAuthorized':False}


def main():
    import boto3
    from botocore.exceptions import ClientError
    p=argparse.ArgumentParser()
    p.add_argument('--settings',default=str(ROOT/'aws/us-east-1.json'))
    p.add_argument('--profile')
    p.add_argument('--stack',default='omega-polygon-137')
    p.add_argument('--commit')
    p.add_argument('--execute',action='store_true')
    p.add_argument('--prepare',action='store_true',help='Create a reviewable change set, without executing it')
    p.add_argument('--owner-authorized-root',action='store_true',
                   help='Use only with an existing explicit owner authorization for root deployments')
    args=p.parse_args()
    settings=json.loads(Path(args.settings).read_text())
    commit=args.commit or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('IMMUTABLE_COMMIT_REQUIRED')
    session=boto3.Session(profile_name=args.profile,region_name=settings['Region'])
    evidence=preflight(session,settings,commit)
    print(json.dumps(evidence,sort_keys=True))
    if not (args.prepare or args.execute):return
    assert_deployer(evidence['identity'],settings['AccountId'],owner_authorized_root=args.owner_authorized_root)
    url=f'https://codeload.github.com/House-Of-Drip-Online/POL-mainnet-full-node/tar.gz/{commit}'
    with urllib.request.urlopen(url,timeout=60) as response:
        archive=response.read(16*1024*1024+1)
    if len(archive)>16*1024*1024:raise ValueError('SOURCE_ARCHIVE_LIMIT')
    parameters={k:settings[k] for k in ['VpcId','SubnetId','AvailabilityZone','ImageId']}
    parameters.update({'SourceCommit':commit,'SourceArchiveSha256':hashlib.sha256(archive).hexdigest()})
    cfn=session.client('cloudformation')
    try:
        cfn.describe_stacks(StackName=args.stack)
        kind='UPDATE'
    except ClientError as exc:
        if exc.response['Error']['Code']!='ValidationError' or 'does not exist' not in str(exc):raise
        kind='CREATE'
    name=f'node-{commit[:12]}-{int(time.time())}'
    response=cfn.create_change_set(StackName=args.stack,ChangeSetName=name,ChangeSetType=kind,
        Description=f'Immutable Polygon node deployment {commit}',
        TemplateBody=(ROOT/'aws/node.yaml').read_text(),Capabilities=['CAPABILITY_IAM'],
        Parameters=[{'ParameterKey':k,'ParameterValue':v} for k,v in parameters.items()],
        Tags=[{'Key':'System','Value':'OMEGA-Polygon-Node'},{'Key':'SourceCommit','Value':commit}])
    change_id=response['Id']
    cfn.get_waiter('change_set_create_complete').wait(ChangeSetName=change_id,
        WaiterConfig={'Delay':5,'MaxAttempts':60})
    change=cfn.describe_change_set(ChangeSetName=change_id)
    changes=change.get('Changes',[])
    while change.get('NextToken'):
        change=cfn.describe_change_set(ChangeSetName=change_id,NextToken=change['NextToken'])
        changes.extend(change.get('Changes',[]))
    assert_nondestructive(changes)
    print(json.dumps({'changeSetId':change_id,'changes':changes},default=str))
    if not args.execute:return
    cfn.execute_change_set(ChangeSetName=change_id)
    cfn.get_waiter('stack_create_complete' if kind=='CREATE' else 'stack_update_complete').wait(
        StackName=args.stack,WaiterConfig={'Delay':15,'MaxAttempts':120})
    stack=cfn.describe_stacks(StackName=args.stack)['Stacks'][0]
    print(json.dumps({'status':'HOST_PROVISIONED_SYNC_UNPROVEN','stackId':stack['StackId'],
        'outputs':stack.get('Outputs',[]),'sourceCommit':commit,'executionAuthorized':False}))


if __name__=='__main__':main()
