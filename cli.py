import click
import datetime
import sys

from mtls import MutualTLS


VERSION = 'v0.7.0'
HELP_TEXT = ('mtls is a PGP Web of Trust based SSL Client Certificate '
             'generation tool based on Googles Beyond Corp Zero Trust '
             'Authentication. Version {}.'.format(VERSION))


@click.group(help=HELP_TEXT)
@click.version_option(VERSION, message="%(version)s")
@click.option(
    '--server', '-s',
    type=str,
    help='Server to run command against.'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='config file. [~/.config/mtls]'
)
@click.option(
    '--gpg-password',
    type=str,
    hidden=True
)
@click.pass_context
def cli(ctx, server, config, gpg_password):
    options = {
        'config': config,
        'gpg_password': gpg_password
    }
    if server is not None:
        ctx.obj = MutualTLS(server, options)
    if sys.platform == 'win32' or sys.platform == 'cygwin':
        click.secho(
            'Your platform is not currently supported',
            fg='red'
        )


@cli.command('create-certificate')
@click.pass_context
def create_cert(ctx):
    if ctx.obj is None:
        click.secho('A server was not provided.', fg='red')
        sys.exit(1)
    ctx.obj.get_crl(False)
    ctx.obj.create_cert()


@cli.command('revoke-certificate')
@click.option(
    '--fingerprint',
    '-f',
    default=None,
    help='User PGP Fingerprint'
)
@click.option(
    '--serial-number',
    default=None,
    help='Serial Number of certificate'
)
@click.option(
    '--name',
    '-n',
    default=None,
    help='The common name on the certificate.'
)
@click.pass_context
def revoke_cert(ctx, fingerprint, serial_number, name):
    if ctx.obj is None:
        click.secho('A server was not provided.', fg='red')
        sys.exit(1)
    ctx.obj.revoke_cert(fingerprint, serial_number, name)

@cli.command()
@click.option(
    '--admin',
    is_flag=True,
    default=False,
    help='Is the user an admin'
)
@click.option(
    '--fingerprint',
    '-f',
    default=None,
    help='User PGP Fingerprint'
)
@click.option(
    '--email',
    '-e',
    default=None,
    help='User email. This will grab the users fingerprint from your local ' +
         'trust store'
)
@click.option(
    '--keyserver',
    default=None,
    help='Keyserver for searching by email. Defaults to pgp.mit.edu'
)
@click.pass_context
def add_user(ctx, admin, fingerprint, email, keyserver):
    if ctx.obj is None:
        click.secho('A server was not provided.', fg='red')
        sys.exit(1)
    if fingerprint is None and email is None:
        click.echo('A fingerprint must be provided')
        sys.exit(1)
    if email is not None:
        fingerprint = handle_email(ctx, email, keyserver)
    ctx.obj.add_user(fingerprint, admin)


@cli.command()
@click.option(
    '--admin',
    is_flag=True,
    default=False,
    help='Is the user an admin'
)
@click.option(
    '--fingerprint',
    '-f',
    default=None,
    help='User PGP Fingerprint'
)
@click.option(
    '--email',
    '-e',
    default=None,
    help='User email. This will grab the users fingerprint from your local ' +
         'trust store'
)
@click.option(
    '--keyserver',
    default=None,
    help='Keyserver for searching by email. Defaults to pgp.mit.edu'
)
@click.pass_context
def remove_user(ctx, admin, fingerprint, email, keyserver):
    if ctx.obj is None:
        click.secho('A server was not provided.', fg='red')
        sys.exit(1)
    if fingerprint is None and email is None:
        click.echo('A fingerprint or email must be provided')
        sys.exit(1)
    if email is not None:
        fingerprint = handle_email(ctx, email, keyserver)

    ctx.obj.remove_user(fingerprint, admin)


@cli.command()
@click.option(
    '--output/--no-output',
    '-o/-no',
    is_flag=True,
    default=True,
    help='Output to stdout. Otherwise this will write to ' +
         '~/.config/mtls/<server>/crl.pem'
)
@click.pass_context
def get_crl(ctx, output):
    if ctx.obj is None:
        click.secho('A server was not provided.', fg='red')
        sys.exit(1)
    ctx.obj.get_crl(output)


def handle_email(ctx, email, keyserver=None):
    if keyserver:
        search_res = ctx.obj.gpg.search_keys(email, keyserver=keyserver)
    else:
        search_res = ctx.obj.gpg.search_keys(email)
    now = str(int(datetime.datetime.now().timestamp()))
    non_expired = []
    for res in search_res:
        if res['expires'] < now:
            continue
        non_expired.append(res)
    if len(non_expired) == 0:
        click.secho('A fingerprint with the key could not be found.')
        sys.exit(1)
    if len(non_expired) == 1:
        return non_expired[0]['keyid']
    for idx, res in enumerate(non_expired):
        click.echo('{idx}) {fingerprint} {uid}'.format(
            idx=idx,
            fingerprint=res['keyid'],
            uid=res['uids'][0]
        ))
    num = len(non_expired)
    value = int(input("Please select a key to add: "))
    if value > num:
        click.secho('Invalid number, exiting')
        sys.exit(1)
    return non_expired[value]['keyid']


if __name__ == '__main__':
    # main()
    cli()
