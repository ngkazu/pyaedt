from ..generic.general_methods import aedt_exception_handler, generate_unique_name
from .Analysis import Analysis
from .Design import solutions_settings
from ..modeler.Circuit import ModelerNexxim
from ..modules.SetupTemplates import SetupKeys
from ..modules.SolveSetup import SetupCircuit


class FieldAnalysisCircuit(Analysis):
    """ **AEDT_CircuitAnalysis**
    Class for Circuit Analysis Setup (Nexxim,)
    It is automatically initialized by Application call (like HFSS, Q3D...). Refer to Application function for inputs definition

    """
    @property
    def solution_type(self):
        return self._solution_type


    @solution_type.setter
    def solution_type(self, soltype):
        """Solution Type


        :param soltype: SolutionType object
        :return:
        """
        if soltype:
            self._solution_type = solutions_settings[soltype]
        else:
            self._solution_type = "NexximLNA"

    @property
    def existing_analysis_setups(self):
        """ Return a list of all defined analysis setup names in the maxwell design.
        """
        oModule = self.odesign.GetModule("SimSetup")
        setups = oModule.GetAllSolutionSetups()
        return setups

    @property
    def nominal_sweep(self):
        """ Return a list of all defined analysis setup names in the maxwell design.
        """
        if self.existing_analysis_setups:
            return self.existing_analysis_setups[0]
        else:
            return ""

    def __init__(self, application, projectname, designname, solution_type, setup_name=None):
        self.solution_type = solution_type
        Analysis.__init__(self, application, projectname, designname, solution_type, setup_name)
        self._modeler = ModelerNexxim(self)
        self._modeler.primitives.init_padstacks()
        #self._post = PostProcessor(self)

    @property
    def modeler(self):
        return self._modeler

    @property
    def oanalysis(self):
        return self.odesign.GetModule("SimSetup")

    @property
    def setup_names(self):
        return self.oanalysis.GetAllSolutionSetups()

    @property
    def get_excitations_name(self):
        """
        Property

        :return: BoundarySetup Module object
        """
        ports = [p.replace('IPort@', '').split(';')[0] for p in self.modeler.oeditor.GetAllPorts()]
        return ports

    @property
    def get_all_sparameter_list(self, excitation_names=[]):
        """
        Get the list of all the SParameter from a list of exitations. If no exitation is provided it will provide a full list of sparameters
        Example: excitation_names ["1","2"] output ["S(1,1)", "S(1,2)", S(2,2)]


        :param excitation_names: list of excitation to include
        :return: list of strin representing Sparameters of excitations
        """
        if not excitation_names:
            excitation_names = self.get_excitations_name
        spar = []
        k = 0
        for i in excitation_names:
            k = excitation_names.index(i)
            while k < len(excitation_names):
                spar.append("S({},{})".format(i, excitation_names[k]))
                k += 1
        return spar

    @aedt_exception_handler
    def get_all_return_loss_list(self, excitation_names=[], excitation_name_prefix=''):
        """
        Get the list of all the Returnloss from a list of exitations. If no exitation is provided it will provide a full list of return Losses
        Example: excitation_names ["1","2"] output ["S(1,1)",, S(2,2)]


        :param excitation_names: list of excitation to include
        :return: list of string representing Return Losses of excitations
        """
        if not excitation_names:
            excitation_names = self.get_excitations_name
        if excitation_name_prefix:
            excitation_names = [i for i in excitation_names if excitation_name_prefix.lower() in i.lower()]
        spar = []
        for i in excitation_names:
            spar.append("S({},{})".format(i, i))
        return spar

    @aedt_exception_handler
    def get_all_insertion_loss_list(self, trlist=[], reclist=[], tx_prefix='', rx_prefix=''):
        """
        Get the list of all the Insertion Losses from two list of exitations (driver and receiver). Optionally prefix can
        be used to retrive driver and receiver names.
        Example: excitation_names ["1"] ["2"] output ["S(1,2)"]


        :param trlist: list of Drivers to include
        :param reclist: list of Receiver to include. Number of Driver = Number of Receiver an
        :param tx_prefix: prefix for TX (eg. "DIE")
        :param rx_prefix: prefix for RX (eg. "BGA")
        :return: list of string representing Insertion Losses of excitations
        """
        spar = []
        if not trlist:
            trlist = [i for i in self.get_excitations_name if tx_prefix in i]
        if not reclist:
            reclist = [i for i in self.get_excitations_name if rx_prefix in i]
        if len(trlist)!= len(reclist):
            self.messenger.add_error_message("TX and RX should be same length lists")
            return False
        for i, j in zip(trlist, reclist):
            spar.append("S({},{})".format(i, j))
        return spar

    @aedt_exception_handler
    def get_next_xtalk_list(self, trlist=[], tx_prefix=""):
        """
        Get the list of all the Near End XTalk a list of exitation. Optionally prefix can
        be used to retrive driver names.
        Example: excitation_names ["1", "2", "3"] output ["S(1,2)", "S(1,3)", "S(2,3)"]


        :param trlist: list of Drivers to include
        :param tx_prefix: prefix for TX (eg. "DIE")
        :return: list of string representing Near End XTalks
        """
        next = []
        if not trlist:
            trlist = [i for i in self.get_excitations_name if tx_prefix in i]
        for i in trlist:
            k = trlist.index(i)+1
            while k < len(trlist):
                next.append("S({},{})".format(i, trlist[k]))
                k += 1
        return next

    @aedt_exception_handler
    def get_fext_xtalk_list(self, trlist=[], reclist=[], tx_prefix='', rx_prefix='', skip_same_index_couples=True):
        """
        Get the list of all the Far End XTalk from 2 lists of exitations. Optionally prefix can
        be used to retrive driver and receivers names. If skip_same_index_couples is true, the tx and rx with same index
        position will be considered insertion losses and excluded from the list
        Example: excitation_names ["1", "2"] ["3","4"] output ["S(1,4)", "S(2,3)"]


        :param trlist: list of Drivers to include
        :param tx_prefix: prefix for TX (eg. "DIE")
        :param reclist: list of Receiver to include
        :param rx_prefix: prefix for RX (eg. "BGA")
        :param skip_same_index_couples: Boolean ignore TX and RX couple with same index

        :return: list of string representing Far End XTalks
        """
        fext = []
        if not trlist:
            trlist = [i for i in self.get_excitations_name if tx_prefix in i]
        if not reclist:
            reclist = [i for i in self.get_excitations_name if rx_prefix in i]
        for i in trlist:
            for k in reclist:
                if not skip_same_index_couples or reclist.index(k)!= trlist.index(i):
                    fext.append("S({},{})".format(i, k))
        return fext

    @aedt_exception_handler
    def get_setup(self, setupname):
        """  Get Setup from current design.


        :param setupname: name of the setup
        :type setupname: str

        :return: setup object
        """
        setuptype = SetupKeys.defaultSetups[self.solution_type]
        setup = SetupCircuit(self, setuptype, setupname, isnewsetup=False)
        if setup.props:
            self.analysis_setup = setupname
        return setup

    @aedt_exception_handler
    def create_setup(self, setupname="MySetupAuto", setuptype=None, props={}):
        """ Create a new Setup.


        :param setupname: optional, name of the new setup
        :param setuptype: optional, setup type. if None, default type will be applied
        :param props: optional dictionary of properties with values
        :return: setup object
        """
        if setuptype is None:
            setuptype = SetupKeys.defaultSetups[self.solution_type]

        name = self.generate_unique_setup_name(setupname)
        setup = SetupCircuit(self, setuptype, name)
        setup.name = name
        setup.create()
        if props:
            for el in props:
                setup.props[el] = props[el]
        setup.update()
        self.analysis_setup = name
        self.setups.append(setup)
        return setup


    # @property
    # def mesh(self):
    #     return self._mesh
    #
    # @property
    # def post(self):
    #     return self._post