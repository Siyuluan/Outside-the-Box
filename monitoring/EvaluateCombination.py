from monitoring import *
from run.Runner import run
from utils import *
from data import *
from trainers import *
import math
import time

def evaluate_all(model_name, model_path, data_name, data_train_model, data_test_model, data_train_monitor,
                 data_test_monitor, data_run, monitor_manager: MonitorManager, alphas=None,
                 model_trainer=StandardTrainer(), seed=0, n_epochs=-1, batch_size=-1,LOF = True):
    # set random seed
    set_random_seed(seed)

    # construct statistics wrapper
    statistics = Statistics()

    # load data
    all_classes_network, labels_network, all_classes_rest, labels_rest = get_data_loader(data_name)(
        data_train_model=data_train_model, data_test_model=data_test_model, data_train_monitor=data_train_monitor,
        data_test_monitor=data_test_monitor, data_run=data_run)

    # load network model or create and train it
    model, history_model = get_model(model_name=model_name, data_train=data_train_model, data_test=data_test_model,
                                     n_classes=len(labels_network), model_trainer=model_trainer, n_epochs=n_epochs,
                                     batch_size=batch_size, statistics=statistics, model_path=model_path)

    print(("Data: classes {} with {:d} inputs (monitor training), classes {} with {:d} inputs (monitor test), " +
          "classes {} with {:d} inputs (monitor run)").format(
        classes2string(data_train_monitor.classes), data_train_monitor.n,
        classes2string(data_test_monitor.classes), data_test_monitor.n,
        classes2string(data_run.classes), data_run.n))

    # normalize and initialize monitors
    monitor_manager.normalize_and_initialize(model, len(labels_rest))

    # train monitors
    #monitor_manager.train(model=model, data_train=data_train_monitor, data_test=data_test_monitor,
    #                      statistics=statistics)

    # run monitors & collect novelties
    #history_run = monitor_manager.run(model=model, data=data_run, statistics=statistics)
    #novelty_wrapper_run = history_run.novelties(data_run, all_classes_network, all_classes_rest)

    #if alphas is None:
    #    return history_run, novelty_wrapper_run, statistics

    # run alpha threshold
    #histories_alpha_thresholding = []
    #novelty_wrappers_alpha_thresholding = []
    #for alpha in alphas:
    #    history_alpha_thresholding = History()
    #    test_alpha(model, data_run, history_alpha_thresholding, alpha)
    #    novelty_wrapper_alpha_thresholding =\
    #        history_alpha_thresholding.novelties(data_run, all_classes_network, all_classes_rest)
    #    histories_alpha_thresholding.append(history_alpha_thresholding)
    #    novelty_wrappers_alpha_thresholding.append(novelty_wrapper_alpha_thresholding)
    layer2values_run, _ = obtain_predictions(model=model, data=data_run, layers=monitor_manager.layers())
    ground_truths_data_run = data_run.ground_truths()
    anomaly_data = 0
    anomaly_labels = []
    for class_id in all_classes_rest:
        if class_id not in all_classes_network:
            anomaly_labels.append(class_id)
    print("anomaly_labels: " + str(anomaly_labels))
    count = 0
    ### LOF
    if(LOF):
        file = 'trainLOF.txt'
        for w in range(2,3): # n_neighbors
            n_neighbors = w *10
            for j in range(1,2): # leaf_size
                leaf_size = j *30
                contamination = 0.03
                for z in range(1): # contamination
                    print("Training "+str(count)+"th LOF is beginning")
                    count = count + 1
                    train_time_begin = time.time()
                    lof_train = monitor_manager.trainLOF(model=model, data_train=data_train_monitor,n_neighbors = n_neighbors ,leaf_size =leaf_size,contamination =contamination)
                    train_time_end = time.time()
                    train_time_all = train_time_end - train_time_begin
                    print(" Run LOF now ")
                    true_negatives = 0
                    false_positives = 0
                    false_negatives = 0
                    true_positives = 0
                    anomaly_data = 0
                    test_time_begin = time.time()
                    monitored_layers = list(reversed(monitor_manager.layers()))
                    for i, (c_ground_truth) in enumerate(zip(ground_truths_data_run)):
                        #countlayer = 0
                        accepts = True
                        #for layer in monitor_manager.layers():
                        for layer in monitored_layers:
                            layer2values_run[layer][i] = np.array(layer2values_run[layer][i])
                            S = lof_train[layer].predict([layer2values_run[layer][i]])
                            if (S[0] == -1):
                                accepts = False
                                break
                        '''
                            if (S[0] == 1):
                                countlayer = countlayer + 1
                            else:
                                countlayer = countlayer
                        if (countlayer == 1):
                            accepts = True
                        else:
                            accepts = False
                        '''
                        if c_ground_truth in anomaly_labels:
                            anomaly_data += 1
                            if accepts:
                                false_negatives += 1
                            else:
                                true_positives += 1
                        else:
                            if accepts:
                                true_negatives += 1
                            else:
                                false_positives += 1
                    contamination = contamination + 0.02 # contamination
                    test_time_end = time.time()
                    test_time_all = test_time_end - test_time_begin
                    with open(file, 'a+') as f:
                        f.write('\n'+ "The result is: " +'\n')
                        f.write("\n ++++++++++++++++++++++++++++++++++++++" + '\n')
                        f.write("How many anomaly_data in dataset:" + str(anomaly_data)+ '\n')
                        f.write("true_negatives=" + str(true_negatives)+ '\n')
                        f.write("false_positives=" + str(false_positives)+ '\n')
                        f.write("false_negatives=" + str(false_negatives)+ '\n')
                        f.write("true_positives=" + str(true_positives)+ '\n')
                        if (true_positives == 0):
                            f.write("true_positives is zero"+ '\n')
                        else:
                            P = true_positives / (true_positives + false_positives)
                            R = true_positives / (true_positives + false_negatives)
                            F1 = (2 * P * R) / (P + R)
                            FPR = false_positives / (false_positives + true_negatives)
                            Accuracy = (true_positives + true_negatives) / (
                                    true_positives + true_negatives + false_positives + false_negatives)
                            f.write("P is: " + str(round(P, 3))+ '\n')
                            f.write("R is: " + str(round(R, 3))+ '\n')
                            f.write("F1 is: " + str(round(F1, 3))+ '\n')
                            f.write("FPR is: " + str(round(FPR, 3))+ '\n')
                            f.write("Accuracy is: " + str(round(Accuracy, 3))+ '\n')
                            f.write("training time begin : " + str(train_time_begin) + '\n')
                            f.write("training time end : " + str(train_time_end) + '\n')
                            f.write("testing time begin : " + str(test_time_begin) + '\n')
                            f.write("testing time end : " + str(test_time_end) + '\n')
                            f.write("train time all : " + str(train_time_all) + '\n')
                            f.write("test time all : " + str(test_time_all) + '\n')
                        f.write("\n ++++++++++++++++ Done ++++++++++++++++"+ '\n')


        print(" Run data of LOF is Done")
    else:
        file = 'trainIF.txt'
        for i in range(3, 4):  # n_estimators
            n_estimators = i * 100
            for i in range(1):  # max_samples
                y = 15 + i
                max_samples = int(math.pow(2, y))
                contamination = 0.03
                for i in range(3):  # contamination
                    print("Training " + str(count) + "th IF is beginning")
                    train_time_begin = time.time()
                    count = count + 1
                    if_train = monitor_manager.trainIF(model=model, data_train=data_train_monitor,
                                                       n_estimators=n_estimators, max_samples=max_samples,
                                                       contamination=contamination)
                    train_time_end = time.time()
                    train_time_all = train_time_end - train_time_begin
                    print(" Testing IF now ")
                    true_negatives = 0
                    false_positives = 0
                    false_negatives = 0
                    true_positives = 0
                    anomaly_data = 0
                    test_time_begin = time.time()
                    monitored_layers = list(reversed(monitor_manager.layers()))
                    for i, (c_ground_truth) in enumerate(zip(ground_truths_data_run)):
                        accepts = True
                        for layer in monitored_layers:
                        #countlayer = 0
                        #for layer in monitor_manager.layers():
                            layer2values_run[layer][i] = np.array(layer2values_run[layer][i])
                            S = if_train[layer].predict([layer2values_run[layer][i]])
                            if (S[0] == -1):
                              accepts = False
                              break
                            '''
                            if (S[0] == 1):
                                countlayer = countlayer + 1
                            else:
                                countlayer = countlayer
                        if (countlayer == 1):
                            accepts = True
                        else:
                            accepts = False
                            '''
                        if c_ground_truth in anomaly_labels:
                            anomaly_data += 1
                            if accepts:
                                false_negatives += 1
                            else:
                                true_positives += 1
                        else:
                            if accepts:
                                true_negatives += 1
                            else:
                                false_positives += 1
                    contamination = contamination + 0.02  # contamination
                    test_time_end = time.time()
                    test_time_all = test_time_end - test_time_begin
                    with open(file, 'a+') as f:
                        f.write('\n' + "The result is: " + '\n')
                        f.write("\n ++++++++++++++++++++++++++++++++++++++" + '\n')
                        f.write("How many anomaly_data in dataset:" + str(anomaly_data) + '\n')
                        f.write("true_negatives=" + str(true_negatives) + '\n')
                        f.write("false_positives=" + str(false_positives) + '\n')
                        f.write("false_negatives=" + str(false_negatives) + '\n')
                        f.write("true_positives=" + str(true_positives) + '\n')
                        if (true_positives == 0):
                            f.write("true_positives is zero" + '\n')
                        else:
                            P = true_positives / (true_positives + false_positives)
                            R = true_positives / (true_positives + false_negatives)
                            F1 = (2 * P * R) / (P + R)
                            FPR = false_positives / (false_positives + true_negatives)
                            Accuracy = (true_positives + true_negatives) / (
                                    true_positives + true_negatives + false_positives + false_negatives)
                            f.write("P is: " + str(round(P, 3)) + '\n')
                            f.write("R is: " + str(round(R, 3)) + '\n')
                            f.write("F1 is: " + str(round(F1, 3)) + '\n')
                            f.write("FPR is: " + str(round(FPR, 3)) + '\n')
                            f.write("Accuracy is: " + str(round(Accuracy, 3)) + '\n')
                            f.write("training time begin : " + str(train_time_begin) + '\n')
                            f.write("training time end : " + str(train_time_end) + '\n')
                            f.write("testing time begin : " + str(test_time_begin) + '\n')
                            f.write("testing time end : " + str(test_time_end) + '\n')
                            f.write("train time all : " + str(train_time_all) + '\n')
                            f.write("test time all : " + str(test_time_all) + '\n')
                            f.write("\n ++++++++++++++++ Done ++++++++++++++++" + '\n')
        print(" Testing IF is Done")

    statistics = statistics
    history_run = histories_alpha_thresholding = novelty_wrapper_run = novelty_wrappers_alpha_thresholding = 0
    return history_run, histories_alpha_thresholding, novelty_wrapper_run, novelty_wrappers_alpha_thresholding, \
           statistics


def evaluate_combination(seed, data_name, data_train_model, data_test_model, data_train_monitor, data_test_monitor,
                         data_run, model_trainer, model_name, model_path, n_epochs, batch_size,
                         monitor_manager: MonitorManager, alpha, confidence_thresholds=None, skip_image_plotting=False):

    # convex-set monitoring
    model, history_abstraction, classes_network, labels_network, classes_rest, labels_rest, statistics = run(
        seed, data_name, data_train_model, data_test_model, data_train_monitor, data_test_monitor, data_run,
        model_trainer, model_name, model_path, n_epochs, batch_size, monitor_manager, confidence_thresholds,
        skip_image_plotting, show_statistics=False)

    # alpha-threshold monitoring
    history_alpha_thresholding = History()
    test_alpha(model, data_run, history_alpha_thresholding, alpha)

    # combinations
    history_combined = CombinedHistory([history_abstraction, history_alpha_thresholding])
    history_conditional_abs_at = ConditionalHistory([history_abstraction], [history_alpha_thresholding], alpha)
    history_conditional_at_abs = ConditionalHistory([history_alpha_thresholding], [history_abstraction], alpha)
    n_monitors = len(monitor_manager.monitors()) + 1

    # bin plots
    plot_false_decisions(monitors=monitor_manager.monitors(), history=history_abstraction,
                         confidence_thresholds=confidence_thresholds)
    plot_false_decisions(monitors=[0], history=history_alpha_thresholding, confidence_thresholds=confidence_thresholds,
                         name="alpha threshold")
    for i in range(1, n_monitors + 1):
        # plot_false_decisions(monitors=[0], history=history_combined, confidence_thresholds=confidence_thresholds,
        #                      n_min_acceptance=i)
        plot_false_decisions(monitors=[0], history=history_combined, confidence_thresholds=confidence_thresholds,
                             n_min_acceptance=-i)
    plot_false_decisions(monitors=[0], history=history_conditional_abs_at, confidence_thresholds=confidence_thresholds,
                         name="abstraction then alpha threshold")
    plot_false_decisions(monitors=[0], history=history_conditional_at_abs, confidence_thresholds=confidence_thresholds,
                         name="alpha threshold then abstraction")

    # pie plots
    # for monitor in monitor_manager.monitors():
    #     m_id = monitor.id()
    #     pie_plot(data_run, m_id, history_abstraction, alpha=confidence_thresholds[0])
    #     pie_plot(data_run, m_id, history_abstraction, alpha=confidence_thresholds[-1])
    # pie_plot(data_run, 0, history_alpha_thresholding, alpha=confidence_thresholds[0])
    # pie_plot(data_run, 0, history_alpha_thresholding, alpha=confidence_thresholds[-1])

    # novelty bin plots
    novelty_wrapper_abstraction = history_abstraction.novelties(data_run, classes_network, classes_rest)
    plot_novelty_detection(monitor_manager.monitors(), novelty_wrapper_abstraction, confidence_thresholds)
    novelty_wrapper_alpha_thresholding = history_alpha_thresholding.novelties(data_run, classes_network, classes_rest)
    plot_novelty_detection([0], novelty_wrapper_alpha_thresholding, confidence_thresholds, name="alpha threshold")
    novelty_wrapper_combined = history_combined.novelties(data_run, classes_network, classes_rest)
    for i in range(1, n_monitors + 1):
        # plot_novelty_detection([0], novelty_wrapper_combined, confidence_thresholds, n_min_acceptance=i)
        plot_novelty_detection([0], novelty_wrapper_combined, confidence_thresholds, n_min_acceptance=-i)
    novelty_wrapper_conditional1 = history_conditional_abs_at.novelties(data_run, classes_network, classes_rest)
    plot_novelty_detection([0], novelty_wrapper_conditional1, confidence_thresholds,
                           name="abstraction then alpha threshold")
    novelty_wrapper_conditional2 = history_conditional_at_abs.novelties(data_run, classes_network, classes_rest)
    plot_novelty_detection([0], novelty_wrapper_conditional2, confidence_thresholds,
                           name="alpha threshold then abstraction")

    # comparison plots
    confidence_threshold1_default = 0.0
    confidence_threshold2_default = alpha
    while True:
        answer = input("Show comparison plots [y, n]? ")
        if answer == "n":
            break
        confidence_threshold1 = input("confidence threshold 1 [empty string for default {:f}]? ".format(
            confidence_threshold1_default))
        confidence_threshold2 = input("confidence threshold 1 [empty string for default {:f}]? ".format(
            confidence_threshold2_default))
        if confidence_threshold1 == "":
            confidence_threshold1 = confidence_threshold1_default
        else:
            confidence_threshold1 = float(confidence_threshold1)
        if confidence_threshold2 == "":
            confidence_threshold2 = confidence_threshold2_default
        else:
            confidence_threshold2 = float(confidence_threshold2)
        plot_decisions_of_two_approaches(monitor_manager.monitors()[0], history_abstraction, confidence_threshold1,
                                         0, history_alpha_thresholding, confidence_threshold2, classes_network,
                                         classes_rest)

    # ROC curve
    for monitor in monitor_manager.monitors():
        ROC_plot(monitor.id(), history_abstraction)
    ROC_plot(0, history_alpha_thresholding, name="alpha threshold")
    for i in range(1, n_monitors + 1):
        # ROC_plot(0, history_combined, n_min_acceptance=i)
        ROC_plot(0, history_combined, n_min_acceptance=-i)
    ROC_plot(0, history_conditional_abs_at, name="abstraction then alpha threshold")
    ROC_plot(0, history_conditional_at_abs, name="alpha threshold then abstraction")

    # print("\nDone! In order to keep the plots alive, this program does not terminate until they are closed.")
    # plt.show()
    answer = input("Save all plots [y, n]? ")
    if answer == "y":
        save_all_figures()


def pie_plot(data_run, monitor_id, history_alpha_thresholding, alpha):
    history_alpha_thresholding.update_statistics(monitor_id, alpha)
    tn = history_alpha_thresholding.true_negatives()
    tp = history_alpha_thresholding.true_positives()
    fn = history_alpha_thresholding.false_negatives()
    fp = history_alpha_thresholding.false_positives()
    fig, ax = initialize_single_plot("Performance of monitor {:d} with confidence >= {:f}".format(monitor_id, alpha))
    plot_pie_chart_single(ax=ax, tp=tp, tn=tn, fp=fp, fn=fn, n_run=data_run.n)


def ROC_plot(monitor_id, history, n_min_acceptance=None, name=None):
    fp_list = []
    tp_list = []
    for alpha in range(0, 100, 1):
        history.update_statistics(monitor_id, float(alpha) / 100.0, n_min_acceptance=n_min_acceptance)
        fp_list.append(history.false_positive_rate())
        tp_list.append(history.true_positive_rate())

    fig, ax = plt.subplots(1, 1)
    if name is None:
        if n_min_acceptance is None:
            name = "{:d}".format(monitor_id)
        else:
            if n_min_acceptance >= 0:
                name = "acceptance {:d}".format(n_min_acceptance)
            else:
                name = "rejection {:d}".format(-n_min_acceptance)
    title = "ROC curve (monitor {})".format(name)
    fig.suptitle(title)
    fig.canvas.set_window_title(title)
    # plot ROC curve
    ax.cla()
    ax.scatter(fp_list, tp_list, marker='^', c="r")
    ax.plot([0, 1], [0, 1], label="baseline", c="k", linestyle=":")
    ax.set_title('ROC curve')
    ax.set_xlabel('False positive rate')
    ax.set_ylabel('True positive rate')
    ax.legend()
    plt.draw()
    plt.pause(0.0001)
