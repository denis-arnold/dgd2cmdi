__doc__ = "test env for debugging of resource proxy generation"

# from pudb import set_trace
from batchxslt import cmdiresource

# set_trace()


dgd_corpus = "/home/kuhn/Data/IDS/svn_rev1233/dgd2_data/metadata/corpora/"
dgd_event = "/home/kuhn/Data/IDS/svn_rev1233/dgd2_data/metadata/events/"
dgd_speakers = "/home/kuhn/Data/IDS/svn_rev1233/dgd2_data/metadata/speakers/"

cmdi_corpus = "/home/kuhn/Data/IDS/svn_rev1233/dgd2_data/dgd2cmdi/cmdiOutput/corpus/"
cmdi_event = "/home/kuhn/Data/IDS/svn_rev1233/dgd2_data/dgd2cmdi/cmdiOutput/event/"
cmdi_speakers = "/home/kuhn/Data/IDS/svn_rev1233/dgd2_data/dgd2cmdi/cmdiOutput/speakers/"

transcripts = "/home/kuhn/Data/IDS/svn_rev1233/dgd2_data/transcripts/"

resourcetree = cmdiresource.ResourceTreeCollection(cmdi_corpus, cmdi_event, cmdi_speakers, transcripts)

resourcetree.build_resourceproxy()

resourcetree.write_cmdi('FOLK', '/tmp/folktest.xml')

# TODO: For corpus labels: every resource must be put into the resource proxy list



