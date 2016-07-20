import pandas as pd


class Action(object):
    def __init__(self, name, actor):
        self.name = name
        self.actor = actor


class ActorAction(Action):
    def __init__(self, name, actor, actorid_field_name, time_generator,
                 activity_generator):
        Action.__init__(self, name, actor)

        self.clock = pd.DataFrame({"clock": 0, "activity": 1.},
                                  index=actor.get_ids())
        self.clock["activity"] = activity_generator.generate(size=len(self.clock.index))
        self.clock["clock"] = time_generator.generate(weights=self.clock["activity"])

        self.time_generator = time_generator
        self.secondary_actors = {}
        self.items = {}
        self.base_fields = {}
        self.secondary_fields = {}
        self.value_conditions = {}
        self.feature_conditions = {}
        self.triggers = {}
        self.impacts = {}
        self.actorid_field_name = actorid_field_name

    def who_acts_now(self):
        """

        :return:
        """
        return self.clock[self.clock["clock"] == 0].index

    def update_clock(self, decrease=1):
        """

        :param decrease:
        :return:
        """
        self.clock["clock"] -= 1

    def set_clock(self, ids, values):
        self.clock.loc[ids, "clock"] = values

    def add_secondary_actor(self, name, actor):
        self.secondary_actors[name] = actor

    def add_item(self, name, item):
        self.items[name] = item

    def add_impact(self, name, attribute, function, parameters):
        """

        :param name:
        :param attribute:
        :param function:
        :param parameters:
        :return:
        """
        if function == "decrease_stock":
            if not parameters.has_key("recharge_action"):
                raise Exception("no recharge action linked to stock decrease")

        self.impacts[name] = (attribute, function, parameters)

    def add_field(self, name, relationship):
        """

        :param name:
        :type relationship: DataFrame
        :param relationship: name of relationship to use (as named in the "relationship" field of the action)
        :param params:
        :return:
        """
        self.base_fields[name] = relationship

    def add_secondary_field(self, name, relationship, params=None):
        """

        :param name:
        :type relationship: DataFrame
        :param relationship: name of relationship to use (as named in the "relationship" field of the action)
        :param params:
        :return:
        """
        self.secondary_fields[name] = (relationship, params)

    def add_value_condition(self, name, actorfield, attributefield, function, parameters):
        self.value_conditions[name] = (actorfield, attributefield, function, parameters)

    def add_feature_condition(self, name, actorfield, attributefield, item, function, parameters):
        self.feature_conditions[name] = (actorfield, attributefield, item, function, parameters)

    def choose_field_values(self, actor_ids):
        """
        Constructs values for all fields produced by this actor action,
        selecting randomly from the "other" side of each declared relationship.

        :param actor_ids: the actor ids being "actioned"
        :return: a dataframe with all fields produced by the action
        """

        field_data = []
        # TODO there's something weird here: if only 1 field is returned, we would maybe like to have f to be the name of the field
        for f_name, relationship in self.base_fields.items():
            field_data.append(relationship.select_one(from_ids=actor_ids,
                                                      named_as=f_name))

        # TODO: as a speed up: we could also filter by actor id before doing
        # the join here
        for f_name, (relationship, rel_parameters) in self.secondary_fields.items():
            field_data.append(
                relationship.select_one(from_ids=actor_ids, named_as=f_name)
            )

        all_fields = reduce(lambda df1, df2: pd.merge(df1, df2, on="from"),
                            field_data)

        return all_fields.rename(columns={"from": "actor_id"})

    def check_post_conditions(self, fields_values):
        """
        runs all post-condition checks related to this action on those action
        results.

        :param fields_values:
        :return: the index of actor ids for which post-conditions are not
        violated
        """

        valid_ids = fields_values.index

        for actorf, attrf, func, param in self.value_conditions.values():
            current_actors = fields_values.loc[valid_ids, actorf].values
            validated = self.actor.check_attributes(current_actors, attrf, func, param)
            valid_ids = valid_ids[validated]

        for actorf, attrf, item, func, param in self.feature_conditions.values():
            current_actors = fields_values.loc[valid_ids, actorf].values
            attr_val = self.actor.get_join(current_actors, attrf)
            validated = self.items[item].check_condition(attr_val, func, param)
            valid_ids = valid_ids[validated]

        return valid_ids

    def make_impacts(self, field_values):
        """

        :param field_values:
        :return:
        """
        for impact_name in self.impacts.keys():

            attribute, function, impact_params = self.impacts[impact_name]

            # TODO there is coupling here between the business scenario
            # we need to externalise this to make the design extensible

            if function == "decrease_stock":
                params = {"values": pd.Series(field_values[impact_params["value"]].values,
                                              index=field_values["actor_id"])}
                ids_for_clock = self.actor.apply_to_attribute(attribute, function, params)
                impact_params["recharge_action"].assign_clock_value(pd.Series(data=0,
                                                                       index=ids_for_clock))

            elif function == "transfer_item":
                params_for_remove = {"items": field_values[impact_params["item"]].values,
                                     "ids": field_values[impact_params["seller_key"]].values}

                params_for_add = {"items": field_values[impact_params["item"]].values,
                                  "ids": field_values[impact_params["buyer_key"]].values}

                self.secondary_actors[impact_params["seller_table"]].apply_to_attribute(attribute,
                                                                                 "remove_item",
                                                                                 params_for_remove)

                self.actor.apply_to_attribute(attribute, "add_item", params_for_add)

    def execute(self):
        act_now = self.who_acts_now()
        field_values = self.choose_field_values(act_now.values)

        if len(field_values.index) > 0:
            passed = self.check_post_conditions(field_values)
            field_values["PASS_CONDITIONS"] = 0
            field_values.loc[passed, "PASS_CONDITIONS"] = 1
            count_passed = len(passed)
            if count_passed > 0:
                self.make_impacts(field_values)

        self.set_clock(act_now, self.time_generator.generate(weights=self.clock.loc[act_now, "activity"]) + 1)
        self.update_clock()

        return field_values.rename(columns={"actor_id": self.actorid_field_name})


class AttributeAction(Action):
    def __init__(self, name, actor, attr_name, actorid_field_name,
                 activity_generator, time_generator,
                 parameters):
        Action.__init__(self, name, actor)

        self.attr_name = attr_name
        self.actorid_field_name = actorid_field_name
        self.parameters = parameters
        self.time_generator = time_generator

        self.clock = pd.DataFrame({"clock": 0, "activity": 1.}, index=actor.get_ids())
        self.clock["activity"] = activity_generator.generate(size=len(self.clock.index))
        self.clock["clock"] = self.time_generator.generate(weights=self.clock["activity"])

    def who_acts_now(self):
        """

        :return:
        """
        return self.clock[self.clock["clock"] == 0].index

    def update_clock(self, decrease=1):
        """

        :param decrease:
        :return:
        """
        self.clock["clock"] -= 1

    def assign_clock_value(self,values):
        self.clock.loc[values.index,"clock"] = values.values

    def execute(self):
        ids, out, values = self.actor.make_attribute_action(self.attr_name,
                                                            self.actorid_field_name,
                                                            self.who_acts_now(),
                                                            self.parameters)

        if len(ids) > 0:
            if values is None:
                self.clock.loc[ids, "clock"] = self.time_generator.generate(weights=self.clock.loc[ids, "activity"])+1
            else:
                self.clock.loc[ids, "clock"] = self.time_generator.generate(weights=values)+1
        self.update_clock()

        return out
