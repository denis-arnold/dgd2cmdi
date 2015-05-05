__author__ = 'kuhn'

import logging
import os
from lxml import etree
import mimetypes

import networkx


# TODO: define paths in csv files
DGDROOT = "dgd2_data"
RESOURCEPROXIES = "ResourceProxyList"
SPEAKERXPATH = "//InEvent/Event"
RESOURCEPATH = "dgd2_data/dgd2cmdi/cmdiOutput/"
PREFIX = 'cmdi_'
NAME = 'AGD'

import urllib

# this is the landing page prefix for the agd werbservice
LANDINGPG = u"http://dgd.ids-mannheim.de/service/DGD2Web/ExternalAccessServlet?command=displayData&id="


class ResourceTreeCollection(networkx.MultiDiGraph):
    """
    represent resources in a tree structure. all involved paths
    The resurce collection is a Digraph representation of all data.
    each data is a node that holds a dict defining their attributes:

    repopath : <path locates the metadata file in the dgd repository scopus>
    corpusroot : <boolean. is the file a corpus catalogue or not?>

    input data paths must be pointed towards already cmdi transformed data.

    NOTE: April 29th
    Speakers are not removed from resource proxy generation. Transcript nodes
    are added. their type is labelled "transcript" accordingly.

    CMDI references only work with new transformed data (revision including
    session to event metadata)
    """

    def __init__(self, corpuspath, eventspath, speakerspath, transcriptspath):
        super(ResourceTreeCollection, self).__init__()
        corpusnames = os.listdir(corpuspath)
        eventcorpusnames = os.listdir(eventspath)
        speakercorpusnames = os.listdir(speakerspath)
        transcriptscorpusnames = os.listdir(transcriptspath)
        self.name = NAME
        # cwdstart = os.getcwd()

        # define a collection root that precedes all corpora
        self.add_node("AGD_root")

        if cmp(corpusnames, eventcorpusnames) and cmp(eventcorpusnames,
                                                      speakercorpusnames):
            logging.info("Resources are aligned")
            print corpusnames
            print eventcorpusnames
            print speakercorpusnames

        else:
            logging.error("Resources are not aligned. Check paths and/ or"
                          "consistency of resource subsets")

        # define corpus nodes

        for corpus in corpusnames:
            # iterate over all corpus file names in corpus metadata dir
            # and define a node for each.
            try:
                etr = etree.parse(corpuspath + '/' + corpus)

            except (etree.XMLSyntaxError, IOError):
                logging.error("Warning. xml file was not parsed: " + corpus)
                continue
            self.add_node(
                corpus.split('_')[1].rstrip('-'),
                {
                    'repopath': self.contextpath(corpus, DGDROOT),
                    'corpusroot': True,
                    'type': 'metadata',
                    'etreeobject': etr,
                    'filename': corpus})

            # add edge from root to current node
            self.add_edge('AGD_root', corpus.split('_')[1].rstrip('-'))

        # define event nodes and add add them to their corpus root

        for event in eventcorpusnames:

            """
            define eventnodes. note that each event has a number of sessions that
            are not explicitly stored as nodes.
            """

            if self.has_node(event):
                eventcorpusfilepath = eventspath + '/' + event

                for filename in os.listdir(eventcorpusfilepath):
                    try:
                        etr = etree.parse(eventcorpusfilepath + '/' + filename)
                    except (etree.XMLSyntaxError, IOError):
                        logging.error("Warning. xml file was not parsed: " + filename)
                        continue

                    eventnodename = filename.split('.')[0].lstrip(PREFIX).rstrip('_extern')
                    self.add_node(eventnodename, {
                        'repopath': self.contextpath(event, DGDROOT),
                        'corpusroot': False,
                        'type': 'metadata',
                        'etreeobject': etr,
                        'filename': filename})

                    self.add_edge(event, eventnodename)
            # finally connect an event to all speakers that take part in it.
            for speaker in self.find_speakers(event):
                self.add_edge(event, speaker)

        # define speaker nodes and add them to their corpus root

        for transcriptcorp in transcriptscorpusnames:

            """
            define transcriptnodes for each corpus found in the primary source folders
            the event that an trancript is counted to is simply derived by splitting the
            string of the transcript filename. naming paradigm will not change so method is
            simple and safe.
            Each transcript is part of a recording session.
            """

            if self.has_node(transcriptcorp):

                transcriptcorpusfilepath = transcriptspath + '/' + transcriptcorp

                for filename in os.listdir(transcriptcorpusfilepath):
                    # contruct node name. eg. from FOLK_E_00004_SE_01_T_01_DF_01.fln
                    transcriptnodename = filename.split('.')[0]

                    self.add_node(transcriptnodename, {
                        'repopath': transcriptcorp,
                        'corpusroot': False,
                        'type': 'transcript',
                        'etreeobject': False,
                        'filename': filename})

                    # obtain event from filename
                    transcriptevent = '_'.join(transcriptnodename.split('_')[:3])
                    # define edge from event to transcript
                    if self.has_node(transcriptevent):
                        self.add_edge(transcriptevent, transcriptnodename)

                    # define an edge to refer from the corpus catalogue to the transcript
                    if self.has_node(transcriptcorp):
                        self.add_edge(transcriptcorp, transcriptnodename)

        for speakercorp in speakercorpusnames:

            """
            define speakernodes. note that each speaker is part of an session
            in an event. to just find the event, a speaker has taken part,
            access the <InEvent> element of the speaker cmdi metadata.
            """

            # find corpus the speaker is part of
            if self.has_node(speakercorp):
                speakercorpusfilepath = speakerspath + '/' + speakercorp

                for filename in os.listdir(speakercorpusfilepath):
                    try:
                        etr = etree.parse(speakercorpusfilepath + '/' + filename)
                    except (etree.XMLSyntaxError, IOError):
                        logging.error("Warning. xml file was not parsed: " +
                                      filename)
                        continue
                    speakernodename = filename.split('.')[0].lstrip(PREFIX).rstrip('_extern')
                    self.add_node(speakernodename, {
                        'repopath': self.contextpath(speakercorp, DGDROOT),
                        'corpusroot': False,
                        'type': 'metadata',
                        'etreeobject': etr,
                        'filename': filename})

                    # define an edge from the parent corpus (speakercorp)
                    # to the current speakernode
                    # example: "PF" --> "PF--_S_00103.xml"
                    self.add_edge(speakercorp, speakernodename)
                    # define edges from events to current speaker

                    speakerevents = self.find_events(speakernodename)
                    for event in speakerevents:
                        if self.has_node(event):
                            self.add_edge(event, speakernodename)

    @staticmethod
    def contextpath(fname, startpath):
        # FIXME: method always returns None.
        """find the path from a startpath to a given file"""
        for root, dirs, files in os.walk(startpath):
            if fname in files:
                return os.path.join(root, fname)
            else:
                return None

    def show_empty_etree(self):
        """
        returns all empty etree attributes for debugging
        :return:
        """
        empties = list()
        for nodename in self.nodes_iter():
            if self.node.get(nodename).get('etreeobject') is None:
                empties.append((nodename, self.node.get(nodename).get('filename')))
        return empties

    def find_eventsessions(self, speakernode):
        """
        :param speakernode
        :return list of event labels
        searches for events a speaker takes part in by looking up the
        metadata itself.
        Since there is no physical resource for sessions, they are not
        filed as nodes.
        """
        expression = "//InEvents/EventSession"
        inevent = self.node.get(speakernode).get("etreeobject").xpath(expression)
        # must add _extern label to find in graph
        # inevent_out = [event.text + '_extern.xml' for event in inevent]
        ineventsessions_out = [event.text for event in inevent]
        return ineventsessions_out

    def find_events(self, speakernode):
        """
        :param speakernode
        :return list of event labels
        searches for events a speaker takes part in by looking up the
        metadata itself.
        """
        sessions = self.find_eventsessions(speakernode)
        # take the session of event label and split it down to the event
        events = ['_'.join(str(segment) for segment in session.split('_')[0:3])
                  for session in sessions]
        events = list(set(events))
        return events

    def find_speakers(self, eventnode):
        """
        returns all speaker nodes connected to the eventnode.
        note april: now using normal
        :param eventnode:
        :return: list of speaker labels fo/und in event
        """

        speakerlist = list()

        # simple split label solution

        for outedge in self.out_edges_iter([eventnode]):

            if outedge[1].split('_')[1] == 'S':
                speakerlist.append(outedge[1])

        return speakerlist

        # xpath solution

        # session = "//Session"
        # speakerpath = "Speaker/Label"
        # sessionsofevent = self.node.get(eventnode).get("etreeobject").xpath(session)
        # speakerlabels = list()
        # #
        # # add all sessions of the event as attribute
        # self.node.get(eventnode).update({'sessions': sessionsofevent})
        # #
        # for session in sessionsofevent:
        #     # must add "_extern" label to find speaker in graphh
        #     speakerlabels.extend([speaker.text for speaker in session.xpath(speakerpath)])
        #     speakerlabels.extend([speaker.text + '_extern.xml' for speaker in session.xpath(speakerpath)])

    def find_transcripts(self, eventnode):
        """
        finds trancripts associated with given event
        :param eventnode:
        :return:
        """
        transcripts = list()
        for nodename in eventnode.out_edges():
            if self.node.get(nodename).get('type') == 'transcript':
                transcripts.append(nodename)

        return transcripts

    def speaker2event(self, eventnode):
        """
        finds all speaker nodes for a given event node and integrates their metadata into
        the event node
        :param eventnode:
        :return:
        """

        eventtree = self.node.get(eventnode).get('etreeobject')

        for speakernode in self.find_speakers(eventnode):

            speaker_name = self.node.get(speakernode).get("etreeobject").find('Name')
            speaker_alias = self.node.get(speakernode).get("etreeobject").find('Alias')
            speaker_id = self.node.get(speakernode).get("etreeobject").find('TranscriptID')
            speaker_sex = self.node.get(speakernode).get("etreeobject").find('Sex')
            speaker_dob = self.node.get(speakernode).get("etreeobject").find('DateOfBirth')
            speaker_edu = self.node.get(speakernode).get("etreeobject").find('Education')
            speaker_occ = self.node.get(speakernode).get("etreeobject").find('Occupation')
            speaker_ethn = self.node.get(speakernode).get("etreeobject").find('Ethnicity')
            speaker_nat = self.node.get(speakernode).get("etreeobject").find('Nationality')
            speaker_loc = self.node.get(speakernode).get("etreeobject").find('LocationData')
            speaker_lang = self.node.get(speakernode).get("etreeobject").find('LanguageData')

            for event_speaker in eventtree.iter('Speaker'):

                if event_speaker.find('Label') == speakernode:

                    etree.SubElement(event_speaker, speaker_name)
                    etree.SubElement(event_speaker, speaker_id)
                    # etree.SubElement(event_speaker, speaker_sex)
                    etree.SubElement(event_speaker, speaker_dob)
                    etree.SubElement(event_speaker, speaker_edu)
                    etree.SubElement(event_speaker, speaker_occ)
                    etree.SubElement(event_speaker, speaker_ethn)
                    etree.SubElement(event_speaker, speaker_nat)
                    etree.SubElement(event_speaker, speaker_loc)
                    etree.SubElement(event_speaker, speaker_lang)

    def define_resourceproxy(self, metafilenode):
        """
        defines the ResourceProxies for all Resources referred via edges
               <Resources>
        <ResourceProxyList> </ResourceProxyList>
        <JournalFileProxyList> </JournalFileProxyList>
        <ResourceRelationList> </ResourceRelationList>
        </Resources>
        :param metafilenode:
        :return:
        """

        cmdi_etrobj = self.node.get(metafilenode).get("etreeobject")
        cmdiroot = cmdi_etrobj.getroot()
        try:
            resourceproxies = cmdiroot.find("Resources").find("ResourceProxyList")
        except AttributeError:
            logging.error("No Resource Element found in " + metafilenode + ". Check cmdi file consistency.")

            return

        in_nodes = [i[0] for i in self.in_edges(metafilenode)]
        out_nodes = [i[1] for i in self.out_edges(metafilenode)]

        resource_nodes = out_nodes + in_nodes

        # remove speaker references for now
        for speaker in self.find_speakers(metafilenode):
            if speaker in resource_nodes:
                resource_nodes.remove(speaker)

        # remove the abstract node from the resource list
        if 'AGD_root' in resource_nodes:
            resource_nodes.remove('AGD_root')
        if metafilenode in resource_nodes:
            resource_nodes.remove(metafilenode)
        # make sure there are just unique references
        resource_nodes = set(resource_nodes)

        for node in resource_nodes:
            # where is the edge pointed to?
            # access the filename

            node_fname = self.node.get(node).get("filename")
            resourceproxy = etree.SubElement(resourceproxies, "ResourceProxy")
            resourceref = etree.SubElement(resourceproxy, "ResourceRef")
            resourcetype = etree.SubElement(resourceproxy, "ResourceType")
            resourceproxy.set("id", node)

            resourcetype.set("mimetype", str(mimetypes.guess_type(node_fname)[0]))
            # if mimetype is unknown set it to 'application/binary'
            # TODO:
            if resourcetype.get("mimetype") == 'None':
                resourcetype.set("mimetype", 'application/xml')

            landingpage = urllib.unquote(LANDINGPG)
            resourceref.text = node
            resourceref.set("href", landingpage + node)

            # Generate an is PartRelationship for backreference
            # TODO: build ispart and isversion of relations
            ispart = etree.SubElement(resourceproxy, "ResourceIsPart")

            # insert new resourceproxyelement in list
            # resourceproxies.append(resourceproxy)

            # version resource info
            # isVersionOf = etree.SubElement(resourceproxies, "isVersionOf")

    def write_cmdi(self, nodename, fname):
        """
        write the cmid-xml of a node to a specified file.
        :param nodename, fname:
        :return:
        """
        self.node.get(nodename).get('etreeobject').write(fname, encoding='utf-8', method='xml')

    def build_resourceproxy(self):
        """
        inplace resourceproxy generation of the resource.
        modifies the stored etree object of each resource.
        :param :
        :return:
        """

        for resource in self.nodes_iter():

            # pass the node name to define_resourceproxy
            if self.node.get(resource).get("etreeobject") \
                    is not False and resource != 'AGD_root':
                self.define_resourceproxy(resource)

                # def build_geolocation(self, nodename):
                # """
                #     inplace computation of the geolocations
                #     :return:
                #     """
                #     # find geolocation package to compute locations
                #     # from the provided grid coordinates
                #
                #     # if provided, obtain grid coordinates.
                #
                #     for node in self.nodes_iter():
                #
                #         pass

    def define_parts(self, resource):
        """
        define Parts for a given node inside a Relation Element.
        all outgoing edges refer to hasParts relations.
        all ingoing edges refer to isPartOf relations.
        :param resource:
        :return:
        """
        cmdi_etrobj = self.node.get(resource).get("etreeobject")
        cmdiroot = cmdi_etrobj.getroot('DGDEvent')

        in_nodes = [i[0] for i in self.in_edges(resource)]
        out_nodes = [i[1] for i in self.out_edges(resource)]

        # hasPart Elements for out_nodes
        # isPartOf Elements for in_nodes

        # remove speaker references for now
        for speaker in self.find_speakers(resource):
            if speaker in out_nodes:
                out_nodes.remove(speaker)

        for speaker in self.find_speakers(resource):
            if speaker in in_nodes:
                in_nodes.remove(speaker)

        # remove the abstract node from the resource lists
        if 'AGD_root' in in_nodes:
            in_nodes.remove('AGD_root')
        # remove the self-reference from the resource lists
        if resource in in_nodes:
            in_nodes.remove(resource)

        # make sure there are just unique references
        in_nodes = set(in_nodes)
        out_nodes = set(out_nodes)

        # define the hasPart Elements
        # define a Relation Element as parent for hasPart elements
        relations = etree.SubElement(cmdiroot, 'Relations')
        # find them in
        for node in out_nodes:

            haspart = etree.SubElement(relations, 'hasPart')
            haspart.set('href', LANDINGPG + node)
            haspart.text = node

        for node in in_nodes:

            ispartof = etree.SubElement(relations, 'isPartOf')
            ispartof.set('href', LANDINGPG + node)
            ispartof.text = node

        # finally, define a node that refers to the version of this metadata
        isversionof = etree.SubElement(relations, 'isVersionOf')
        isversionof.set('href', LANDINGPG + resource)
        isversionof.text = 'Version 0'

    def build_parts(self):
        """
        build the hasPart Relations for all Nodes
        :return:
        """
        for resource in self.nodes_iter():

            # pass the node name to define_resourceproxy
            if self.node.get(resource).get("etreeobject") \
                    is not False and resource != 'AGD_root':
                self.define_parts(resource)

