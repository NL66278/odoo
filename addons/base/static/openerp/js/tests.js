/**
 * @function
 * Defines a module scope (which lasts until the next call to module).
 *
 * This module scopes implies setup and teardown callbacks running for each test.
 *
 * @param {String} name the name of the module
 * @param {Object} [lifecycle] callbacks to run before and after each test of the module
 * @param {Function} lifecycle.setup function running before each test of this module
 * @param {Function} lifecycle.teardown function running after each test of this module
 */
var module;
/**
 * @function
 * Defines a given test to run. Runs all the assertions present in the test
 *
 * @param {String} name the name of the test
 * @param {Number} [expected] number of assertions expected to run in this test (useful for asynchronous tests)
 * @param {Function} test the testing code to run, holding a sequence of assertions (at least one)
 */
var test;
/**
 * @function
 * Defines an asynchronous test: equivalent to calling stop() at the start of
 * a normal test().
 *
 * The test code needs to restart the test runner via start()
 * 
 * @param {String} name the name of the test
 * @param {Number} [expected] number of assertions expected to run in this test (useful for asynchronous tests)
 * @param {Function} test the testing code to run, holding a sequence of assertions (at least one)
 */
var asyncTest;
/**
 * @function
 * The most basic boolean assertion (~assertTrue or assert).
 *
 * Passes if its argument is truthy
 *
 * @param {Boolean} state an arbitrary expression, evaluated in a boolean context
 * @param {String} [message] the message to output with the assertion result
 */
var ok;
/**
 * @function
 * Equality assertion (~assertEqual)
 *
 * Passes if both arguments are equal (via <code>==</code>)
 *
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var equal;
/**
 * @function
 * Inequality assertion (~assertNotEqual)
 *
 * Passes if the arguments are different (via <code>!=</code>)
 *
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var notEqual;
/**
 * @function
 * Recursive equality assertion.
 *
 * Works on primitive types using <code>===</code> and traversing through
 * Objects and Arrays as well checking their components
 * 
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var deepEqual;
var notDeepEqual, strictEqual, notStrictEqual, raises;
/**
 * @function
 * Starts running the test runner again from the point where it was
 * <code>stop</code>ped.
 *
 * Used to resume testing after a callback.
 */
var start;
/**
 * @function
 * Stops the test runner in order to wait for an asynchronous test to run
 *
 * @param {Number} [timeout] fails the test after the timeout triggers, only for debugging tests
 */
var stop;

var Session = function () {
    return {
        rpc: function (_url, params, on_success) {
            setTimeout(on_success);
        }
    };
};
$(document).ready(function () {
    var openerp;
    module("ids_callback", {
        setup: function () {
            openerp = window.openerp.init();
        }
    });
    asyncTest("Baseline event attributes", 6, function () {
        var dataset = new openerp.base.DataSet(
                new Session());
        dataset.on_ids.add(function (records, event) {
            deepEqual(records, [], 'No records returned');
            equal(event.offset, 0, 'No offset set in call');
            equal(event.limit, null, 'No limit set in call');
            deepEqual(event.domain, [], 'No domain on the dataset');
            deepEqual(event.context, {}, 'No context on the dataset');
            deepEqual(event.sort, [], 'The dataset is not sorted');
            start();
        });
        dataset.ids();
    });
    asyncTest("Offset and limit", 2, function () {
        var dataset = new openerp.base.DataSet(
                new Session());
        dataset.on_ids.add(function (records, event) {
            equal(event.offset, 20);
            equal(event.limit, 42);
            start();
        });
        dataset.ids(20, 42);
    });
    asyncTest("Domain and context propagation", 3, function () {
        var dataset = new openerp.base.DataSet(
                new Session());
        var domain_value = [['foo', '=', 'bar']];
        var context_value= {active_id:3, active_ids:42};
        var sort_value = ['foo'];
        dataset.on_ids.add(function (records, event) {
            deepEqual(event.domain, domain_value);
            deepEqual(event.context, context_value);
            deepEqual(event.sort, sort_value);
            start();
        });
        dataset.set({
            domain: domain_value,
            context: context_value,
            sort: sort_value
        });
        dataset.ids();
    });
    asyncTest("Data records", function () {
        var dataset = new openerp.base.DataSet({
            rpc: function (url, _params, on_success) {
                equal('/base/dataset/load', url);
                _.delay(on_success, 0, [
                    {id: 1, sequence: 3, name: "dummy", age: 42},
                    {id: 5, sequence: 7, name: "whee", age: 55}
                ]);
            }
        });
        dataset.on_ids.add(function (records) {
            equal(records.length, 2, "I loaded two virtual records");
            var d1 = records[0],
                d2 = records[1];
            ok(d1 instanceof openerp.base.DataRecord);
            ok(d2 instanceof openerp.base.DataRecord);
            start();
        });
        dataset.ids();
    });

    var dataset;
    module("set", {
        setup: function () {
            var openerp = window.openerp.init();
            dataset = new openerp.base.DataSet();
        }
    });
    test('Basic properties setting', function () {
        var domain_value = [['foo', '=', 'bar']];
        var result = dataset.set({
            domain: domain_value
        });
        ok(dataset === result);
        deepEqual(domain_value, dataset._domain);
    });
    test("Ensure changes don't stick", function () {
        var domain = [['foo', '=', 'bar']];
        dataset.set({
            domain: domain
        });
        domain.pop();
        deepEqual([['foo', '=', 'bar']], dataset._domain);
    });
});
