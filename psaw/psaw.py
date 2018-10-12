import click
from PushshiftAPI import PushshiftAPI
import writers as wt
import utilities as ut

@click.command()
@click.argument('search_type', type=click.Choice(['comments', 'submissions']), default='csv')
@click.option("-q", "--query", help='search term(s)', type=str)
@click.option("-s", "--subreddits", help='restrict search to subreddit(s)', type=str)
@click.option("-a", "--authors", help='restrict search to author(s)', type=str)
@click.option("-l", "--limit", default=20, help='maximum number of items to retrieve')
@click.option("-o", "--output", type=click.File(mode='w'),
              help="output file for saving all results in a single file")
@click.option("--output-template", type=str,
              help="output file name template for saving each result in a separate file")
@click.option('--format', type=click.Choice(['json', 'csv']), default='csv')
@click.option("-f", "--fields", type=str,
              help="fields to retrieve (must be in quotes or have no spaces), defaults to all")
@click.option("--prettify", is_flag=True, default=False,
              help="make output slighly less ugly (for json only)")
@click.option("--dry-run", is_flag=True, default=False,
              help="print potential names of output files, but don't actually write any files")
@click.option("--proxy")
def psaw(search_type, query, subreddits, authors, limit,
         output, output_template, format, fields, prettify, dry_run, proxy):

    if output is None and output_template is None:
        raise click.UsageError("must supply either --output or --output-template")

    if output is not None and output_template is not None:
        raise click.UsageError("can only supply --output or --output-template, not both")

    if output:
        batch_mode = True
    else:
        batch_mode = False

    api = PushshiftAPI()
    search_args = dict()

    query = ut.string_to_list(query)
    fields = ut.string_to_list(fields)
    authors = ut.string_to_list(authors)
    subreddits = ut.string_to_list(subreddits)

    # use a dict to pass args to search function because certain parameters
    # don't have defaults (eg, passing filter=None returns no fields)
    search_args = ut.build_search_kwargs(
        search_args,
        q=query,
        subreddit=subreddits,
        author=authors,
        limit=limit,
        filter=fields,
    )

    search_functions = {
        'comments': api.search_comments,
        'submissions': api.search_submissions,
    }[search_type]

    things = search_functions(**search_args)
    thing, things = ut.peek_first_item(things)
    if thing is None:
        click.secho("no results found", err=True, bold=True)
        return

    fields, missing_fields = ut.validate_fields(thing, fields)

    if missing_fields:
        missing_fields = sorted(missing_fields)
        click.secho("following fields were not retrieved: {}".format(missing_fields),
                    bold=True, err=True)

    writer_class = choose_writer_class(format, batch_mode)
    writer = writer_class(fields=fields, prettify=prettify)

    if batch_mode:
        save_to_single_file(things, output, writer=writer, count=limit, dry_run=dry_run)
    else:
        save_to_multiple_files(things, output_template, writer=writer,
                               count=limit, dry_run=dry_run)


def choose_writer_class(format, batch_mode):
    """
    Choose appropriate writer class

    :param format: str
    :param batch_mode: bool
    :return: Class

    """
    writer_cls = {
        ('json', False): wt.JsonWriter,
        ('json', True): wt.JsonBatchWriter,
        ('csv', True): wt.CsvBatchWriter,
    }[(format, batch_mode)]

    return writer_cls


def save_to_single_file(things, output_file, writer, count, dry_run=False):
    writer.open(output_file)
    writer.header()
    try:
        with click.progressbar(things, length=count) as things:
            for thing in things:
                if not dry_run:
                    writer.write(thing.d_)
    finally:
        writer.footer()
        writer.close()


def save_to_multiple_files(things, output_template, writer, count, dry_run=False):
    if dry_run:
        progressbar = ut.DummyProgressBar(things)
    else:
        progressbar = click.progressbar(things, length=count)

    with progressbar as things:
        for thing in things:
            output_file = output_template.format(**thing.d_)
            if dry_run:
                print("saving to: {}".format(output_file))
            else:
                try:
                    writer.open(output_file)
                    writer.header()
                    writer.write(thing.d_)
                    writer.footer()
                finally:
                    writer.close()


if __name__ == '__main__':
    psaw()



