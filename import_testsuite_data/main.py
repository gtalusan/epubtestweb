import argparse
import os
import yaml
import epub_parser
import import_testsuite
from testsuite_app import models
from testsuite_app import helper_functions
from testsuite_app import export_data
from random import randrange

def print_testsuite(args):
    rs = models.ReadingSystem.objects.get(id=1)
    res = helper_functions.get_results_as_nested_categories(rs)
    for r in res:
        helper_functions.print_item_summary(r)

def clear_data(args):
    models.UserProfile.objects.all().delete()
    models.ReadingSystem.objects.all().delete()

# look at each referenced epub in the categories.yaml file
# parse it and put the data under a category header
def add_testsuite(args):
    print "Processing {0}".format(args.source)
    old_testsuite = models.TestSuite.objects.get_most_recent_testsuite()
    testsuite = import_testsuite.create_testsuite()
    yaml_categories = yaml.load(open("categories.yaml").read())['Categories']

    for cat in yaml_categories:
        new_category = import_testsuite.add_category('1', cat['Name'], None, testsuite)
        for epub in cat['Files']:
            fullpath = os.path.join(args.source, epub)
            if os.path.isdir(fullpath):
                # this will add a new testsuite
                epubparser = epub_parser.EpubParser()
                epubparser.parse(fullpath, new_category, testsuite, cat['CategoryDisplayDepthLimit'])
            else:
                print "Not a directory: {0}".format(fullpath)

    import_testsuite.migrate_data(old_testsuite)

def add_user(args):
    user = models.UserProfile.objects.create_user(args.username, args.email, args.password)
    user.first_name = args.firstname
    user.last_name = args.lastname
    user.is_superuser = False
    user.save()
    return user

def add_rs(args):
    user = models.UserProfile.objects.all()[0]
    rs = models.ReadingSystem(
        locale = "US",
        name = "SuperReader",
        operating_system = "OSX",
        sdk_version = "N/A",
        version = "1.0",
        user = user,
    )
    rs.save() # save now to generate an initial evaluation
    evaluation = rs.get_current_evaluation()
    evaluation.evaluation_type = "2" # public
    # generate result data
    results = evaluation.get_all_results()
    for r in results:
        r.result = str(randrange(1, 4))
        r.save()
    evaluation.save()
    return rs

# settings.py must contain a definition for the 'previous' database in order for this to work
def copy_users(args):
    users = models.UserProfile.objects.using('previous').all()
    for u in users:
        u.save(using='default')
    print "Copied users from old database."

def rollback(args):
    "roll back to the previous testsuite version, or just remove eval data if there is no previous version"
    ts = models.TestSuite.objects.get_most_recent_testsuite()
    evals = models.Evaluation.objects.filter(testsuite = ts)
    for e in evals:
        e.delete()
    ts.delete()

def export(args):
    xmldoc = export_data.export_all_current_evaluations()
    xmldoc.write(args.file)
    print "Data exported to {0}".format(args.file)

def main():
    argparser = argparse.ArgumentParser(description="Collect tests")
    subparsers = argparser.add_subparsers(help='commands')
    import_parser = subparsers.add_parser('import', help='Import a testsuite into the database')
    import_parser.add_argument("source", action="store", help="Folder containing EPUBs")
    import_parser.set_defaults(func = add_testsuite)

    print_parser = subparsers.add_parser('print', help="Print (some) contents of the database")
    print_parser.set_defaults(func = print_testsuite)

    clear_data_parser = subparsers.add_parser('clear', help="Clear user and reading system data from the database")
    clear_data_parser.set_defaults(func = clear_data)

    add_user_parser = subparsers.add_parser('add-user', help="Add a new user")
    add_user_parser.add_argument('username', action="store", help="username")
    add_user_parser.add_argument('password', action="store", help="password")
    add_user_parser.add_argument('email', action="store", help="email")
    add_user_parser.add_argument('--firstname', action="store", help="first name", default="")
    add_user_parser.add_argument('--lastname', action="store", help="last name", default="")
    add_user_parser.set_defaults(func = add_user)

    add_rs_parser = subparsers.add_parser('add-rs', help="Add a new reading system")
    add_rs_parser.set_defaults(func = add_rs)

    copy_users_parser = subparsers.add_parser('copy-users', help="Copy all users")
    copy_users_parser.set_defaults(func = copy_users)

    rollback_parser = subparsers.add_parser('rollback', help="Roll back to the previous testsuite")
    rollback_parser.set_defaults(func = rollback)

    export_parser = subparsers.add_parser('export', help="Export evaluation data for all reading systems")
    export_parser.add_argument("file", action="store", help="store the xml file here")
    export_parser.set_defaults(func = export)

    args = argparser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
